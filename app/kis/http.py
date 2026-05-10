"""KIS HTTP 클라이언트 — 인증 헤더 부착, 레이트 리미터 통합, 에러 처리."""

from __future__ import annotations

import json
import time
from typing import Any

import requests

from app.kis.auth import get_access_token, invalidate
from app.kis.config import KisEnvironment, get_env_config
from app.kis.credentials import KisCredentials, load_credentials
from app.kis.exceptions import KisAuthError, KisError, KisHttpError, KisOrderRejected, KisRateLimitError
from app.kis.rate_limiter import acquire as rate_acquire
from app.utils.logging import get_logger

_log = get_logger("kis.http")


class KisHttpClient:
    """환경 1개에 바인딩된 HTTP 클라이언트 — Session + rate limit + 인증."""

    def __init__(self, env: KisEnvironment, *, custtype: str = "P") -> None:
        self.env = env
        self.cfg = get_env_config(env)
        self.creds: KisCredentials = load_credentials(env)
        self.custtype = custtype  # P: 개인, B: 법인
        self._session = requests.Session()

    # ---- 핵심 호출 ----
    def get(
        self,
        path: str,
        *,
        tr_id: str,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict:
        return self._request("GET", path, tr_id=tr_id, params=params, extra_headers=extra_headers)

    def post(
        self,
        path: str,
        *,
        tr_id: str,
        body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict:
        return self._request("POST", path, tr_id=tr_id, body=body, extra_headers=extra_headers)

    def hashkey(self, body: dict[str, Any]) -> str:
        """주문 직전 해시키 발급. 결과 'HASH' 헤더용 문자열 반환."""
        url = f"{self.cfg.base_url}/uapi/hashkey"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "appkey": self.creds.app_key,
            "appsecret": self.creds.app_secret,
        }
        rate_acquire(self.env)
        resp = self._session.post(url, headers=headers, data=json.dumps(body), timeout=10)
        if resp.status_code != 200:
            raise KisHttpError(resp.status_code, resp.text)
        data = resp.json()
        h = data.get("HASH")
        if not h:
            raise KisError(f"hashkey response missing HASH: {data}")
        return h

    # ---- 내부 ----
    def _request(
        self,
        method: str,
        path: str,
        *,
        tr_id: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        _retried: bool = False,
    ) -> dict:
        url = f"{self.cfg.base_url}{path}"
        token = get_access_token(self.env)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
            "appkey": self.creds.app_key,
            "appsecret": self.creds.app_secret,
            "tr_id": tr_id,
            "custtype": self.custtype,
        }
        if extra_headers:
            headers.update(extra_headers)

        rate_acquire(self.env)
        try:
            if method == "GET":
                resp = self._session.get(url, headers=headers, params=params or {}, timeout=15)
            else:
                resp = self._session.post(
                    url, headers=headers, data=json.dumps(body or {}), timeout=15
                )
        except requests.RequestException as exc:
            raise KisHttpError(0, str(exc), f"network error: {exc}") from exc

        # 401 → 토큰 무효화 후 1회 재시도
        if resp.status_code == 401 and not _retried:
            _log.warning("[%s] 401 — invalidating token cache and retrying", self.env.value)
            invalidate(self.env)
            return self._request(
                method, path,
                tr_id=tr_id, params=params, body=body,
                extra_headers=extra_headers, _retried=True,
            )

        if resp.status_code == 429:
            if not _retried:
                _log.warning("[%s] HTTP 429 — backoff and retry", self.env.value)
                time.sleep(1.2)
                return self._request(
                    method, path,
                    tr_id=tr_id, params=params, body=body,
                    extra_headers=extra_headers, _retried=True,
                )
            raise KisRateLimitError(f"HTTP 429 from KIS: {resp.text[:200]}")
        if resp.status_code == 500:
            # KIS는 rate limit를 종종 HTTP 500 + msg_cd EGW00201로 반환
            try:
                body_json = resp.json()
                msg_cd = body_json.get("msg_cd", "")
                msg = body_json.get("msg1", body_json.get("message", ""))
                if msg_cd in {"EGW00201", "EGW00133"} and not _retried:
                    _log.warning("[%s] HTTP 500 + %s — backoff and retry", self.env.value, msg_cd)
                    time.sleep(1.2)
                    return self._request(
                        method, path,
                        tr_id=tr_id, params=params, body=body,
                        extra_headers=extra_headers, _retried=True,
                    )
                if msg_cd:
                    raise KisError(f"HTTP 500 [{msg_cd}] {msg}")
            except (json.JSONDecodeError, ValueError):
                pass
        if resp.status_code == 401:
            raise KisAuthError(f"HTTP 401 after retry: {resp.text[:200]}")
        if resp.status_code >= 400:
            raise KisHttpError(resp.status_code, resp.text)

        data = resp.json()
        rt_cd = data.get("rt_cd")
        if rt_cd is not None and rt_cd != "0":
            msg_cd = data.get("msg_cd", "")
            msg = data.get("msg1", data.get("msg", ""))
            # 레이트 한도: 1회 자동 백오프 후 재시도
            if msg_cd in {"EGW00201", "EGW00133"} and not _retried:
                wait = 1.2
                _log.warning("[%s] %s — backoff %.1fs and retry", self.env.value, msg_cd, wait)
                time.sleep(wait)
                return self._request(
                    method, path,
                    tr_id=tr_id, params=params, body=body,
                    extra_headers=extra_headers, _retried=True,
                )
            if msg_cd in {"EGW00201", "EGW00133"}:
                raise KisRateLimitError(f"[{msg_cd}] {msg}")
            # 주문 관련 거부는 별도 예외
            if path.startswith("/uapi/") and ("order" in path or "trading" in path):
                raise KisOrderRejected(msg_cd, msg)
            raise KisError(f"[{msg_cd}] {msg}")
        return data
