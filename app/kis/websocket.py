"""KIS WebSocket 실시간 시세.

⚠️ 중요: KIS 모의투자(VTS)는 WebSocket 미지원. 실전(prod) 키만 가능.
본 앱은 실전 거래를 권장하지 않으므로 WebSocket은 옵션 기능으로 제공.
일반 시세는 REST 폴링 + Streamlit 자동 새로고침으로 충분.

지원 TR_ID (국내주식):
- H0STCNT0  실시간 주식 체결가
- H0STASP0  실시간 주식 호가

메시지 형식: pipe(`^`) 구분자 텍스트. 첫 문자는 암호화 여부 (0/1).
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Awaitable, Callable

import requests
import websockets

from app.kis.config import KisEnvironment, get_env_config
from app.kis.credentials import load_credentials
from app.kis.exceptions import KisError


def approval_key(env: KisEnvironment) -> str:
    """WebSocket 접속용 approval key 발급."""
    cfg = get_env_config(env)
    creds = load_credentials(env)
    url = f"{cfg.base_url}/oauth2/Approval"
    payload = {
        "grant_type": "client_credentials",
        "appkey": creds.app_key,
        "secretkey": creds.app_secret,
    }
    resp = requests.post(url, json=payload, timeout=10)
    if resp.status_code != 200:
        raise KisError(f"approval failed: HTTP {resp.status_code} {resp.text[:200]}")
    body = resp.json()
    key = body.get("approval_key")
    if not key:
        raise KisError(f"approval response missing key: {body}")
    return key


@dataclass
class TickMessage:
    """실시간 체결가 메시지 (H0STCNT0)."""

    ticker: str
    price: float
    volume: int
    change: float
    change_pct: float
    raw: str


def parse_tick_payload(payload: str, *, tr_id: str = "H0STCNT0") -> TickMessage | None:
    """KIS 실시간 체결가 메시지 파싱.

    형식: <enc>|<tr_id>|<count>|<body...>  (body는 ^로 구분된 필드)
    국내주식 체결가 필드 순서: 종목코드, 체결시각, 현재가, 전일대비부호,
    전일대비, 등락률, ... (총 ~46개 필드)
    """
    if not payload or not payload[0].isdigit():
        return None
    parts = payload.split("|", 3)
    if len(parts) < 4:
        return None
    if parts[1] != tr_id:
        return None
    body = parts[3].split("^")
    if len(body) < 6:
        return None

    def _f(idx: int, default: float = 0.0) -> float:
        if idx >= len(body):
            return default
        v = body[idx]
        if v in ("", None):
            return default
        try:
            return float(v)
        except ValueError:
            return default

    try:
        return TickMessage(
            ticker=body[0],
            price=_f(2),
            volume=int(_f(12)),  # CNTG_VOL — 비어있으면 0
            change=_f(4),
            change_pct=_f(5),
            raw=payload,
        )
    except (ValueError, IndexError):
        return None


async def subscribe_ticks(
    ticker: str,
    env: KisEnvironment,
    on_tick: Callable[[TickMessage], Awaitable[None] | None],
    *,
    tr_id: str = "H0STCNT0",
    duration_sec: float = 30.0,
) -> int:
    """단발 구독 데모: 일정 시간 동안 체결가 수신, 받은 메시지 수 반환."""
    if env.is_mock:
        raise KisError(
            "KIS 모의투자(VTS)는 WebSocket 미지원. 실전 키 환경에서만 사용 가능."
        )
    cfg = get_env_config(env)
    key = approval_key(env)
    sub_msg = {
        "header": {
            "approval_key": key,
            "custtype": "P",
            "tr_type": "1",
            "content-type": "utf-8",
        },
        "body": {"input": {"tr_id": tr_id, "tr_key": ticker}},
    }
    received = 0

    async with websockets.connect(cfg.websocket_url) as ws:
        await ws.send(json.dumps(sub_msg))
        try:
            async with asyncio.timeout(duration_sec):
                async for raw in ws:
                    if not isinstance(raw, str):
                        continue
                    if raw.startswith("{"):
                        # PINGPONG 또는 응답 ack
                        continue
                    tick = parse_tick_payload(raw, tr_id=tr_id)
                    if tick is None:
                        continue
                    received += 1
                    result = on_tick(tick)
                    if asyncio.iscoroutine(result):
                        await result
        except (asyncio.TimeoutError, TimeoutError):
            pass
    return received
