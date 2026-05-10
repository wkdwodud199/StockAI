"""KIS OAuth2 토큰 발급 + 디스크 캐시.

- POST /oauth2/tokenP
- 토큰은 90일 유효. day-80에 도달하면 재발급.
- 캐시: .kis_cache/token_<env>.json
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import typer

from app.kis.config import EnvConfig, KisEnvironment, get_env_config, parse_env
from app.kis.credentials import KisCredentials, load_credentials
from app.kis.exceptions import KisAuthError
from app.kis.utils_paths import KIS_CACHE_DIR  # below import-cycle guard

def _token_path(env: KisEnvironment) -> Path:
    KIS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return KIS_CACHE_DIR / f"token_{env.value}.json"


@dataclass
class CachedToken:
    access_token: str
    expires_at: float  # epoch seconds
    issued_at: float

    def is_valid(self, leeway: float | None = None) -> bool:
        """기본 leeway = max(60s, 토큰 수명의 5%).

        - 실전 90일 토큰 → 약 4.5일 leeway
        - 모의 24시간 토큰 → 약 72분 leeway
        """
        if leeway is None:
            lifetime = max(0.0, self.expires_at - self.issued_at)
            leeway = max(60.0, lifetime * 0.05)
        return self.expires_at - time.time() > leeway

    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "expires_at": self.expires_at,
            "issued_at": self.issued_at,
            "issued_at_iso": datetime.fromtimestamp(self.issued_at, tz=timezone.utc).isoformat(),
            "expires_at_iso": datetime.fromtimestamp(self.expires_at, tz=timezone.utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CachedToken":
        return cls(
            access_token=d["access_token"],
            expires_at=float(d["expires_at"]),
            issued_at=float(d["issued_at"]),
        )


def _read_cache(env: KisEnvironment) -> CachedToken | None:
    p = _token_path(env)
    if not p.exists():
        return None
    try:
        return CachedToken.from_dict(json.loads(p.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def _write_cache(env: KisEnvironment, token: CachedToken) -> None:
    _token_path(env).write_text(json.dumps(token.to_dict(), indent=2), encoding="utf-8")


def _request_new_token(creds: KisCredentials, cfg: EnvConfig) -> CachedToken:
    url = f"{cfg.base_url}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": creds.app_key,
        "appsecret": creds.app_secret,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
    except requests.RequestException as exc:
        raise KisAuthError(f"token request network error: {exc}") from exc

    if resp.status_code != 200:
        raise KisAuthError(f"token request failed: HTTP {resp.status_code} {resp.text[:200]}")

    body = resp.json()
    access_token = body.get("access_token")
    expires_in = int(body.get("expires_in", 0))
    if not access_token or expires_in <= 0:
        raise KisAuthError(f"malformed token response: {body}")

    issued = time.time()
    return CachedToken(
        access_token=access_token,
        expires_at=issued + expires_in,
        issued_at=issued,
    )


def get_access_token(env: KisEnvironment, *, force: bool = False) -> str:
    """환경 토큰을 반환 (캐시 hit 또는 새 발급)."""
    if not force:
        cached = _read_cache(env)
        if cached and cached.is_valid():
            return cached.access_token

    creds = load_credentials(env)
    cfg = get_env_config(env)
    token = _request_new_token(creds, cfg)
    _write_cache(env, token)
    return token.access_token


def invalidate(env: KisEnvironment) -> None:
    p = _token_path(env)
    if p.exists():
        p.unlink()


# ---------- typer CLI ----------
app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def issue(
    env: str = typer.Option(..., "--env", help="KIS 환경 (예: mock_domestic, real_domestic)"),
    force: bool = typer.Option(False, "--force", help="캐시 무시하고 강제 재발급"),
) -> None:
    """토큰 발급/조회."""
    e = parse_env(env)
    token = get_access_token(e, force=force)
    cache = _read_cache(e)
    typer.echo(f"env={e.value}")
    typer.echo(f"access_token={token[:18]}...{token[-6:]}  ({len(token)} chars)")
    if cache:
        exp = datetime.fromtimestamp(cache.expires_at, tz=timezone.utc)
        remaining = timedelta(seconds=int(cache.expires_at - time.time()))
        typer.echo(f"expires_at={exp.isoformat()}  (in {remaining})")
        typer.echo(f"cache_path={_token_path(e)}")


if __name__ == "__main__":
    app()
