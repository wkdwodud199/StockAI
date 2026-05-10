"""KIS WebSocket 실시간 시세 — MVP 골격.

- approval_key 발급 (REST POST /oauth2/Approval)
- 구독 메시지 송신 → 체결가/호가 스트림
- 실 사용은 후속 task로. 본 모듈은 approval_key 검증과 단발 구독 데모까지.
"""

from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

import requests
import websockets

from app.kis.config import KisEnvironment, get_env_config
from app.kis.credentials import load_credentials
from app.kis.exceptions import KisError


def approval_key(env: KisEnvironment) -> str:
    """WebSocket 접속용 approval key 발급 (단명)."""
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


async def subscribe_realtime_price(
    ticker: str,
    env: KisEnvironment,
    on_message: Callable[[dict], Awaitable[None] | None],
    *,
    tr_id: str = "H0STCNT0",  # 국내주식 실시간 체결
    duration_sec: float = 10.0,
) -> None:
    """단발성 구독 데모: 일정 시간 동안 메시지 수신 후 종료."""
    cfg = get_env_config(env)
    key = approval_key(env)
    sub_msg = {
        "header": {
            "approval_key": key,
            "custtype": "P",
            "tr_type": "1",  # 1=등록
            "content-type": "utf-8",
        },
        "body": {"input": {"tr_id": tr_id, "tr_key": ticker}},
    }
    async with websockets.connect(cfg.websocket_url) as ws:
        await ws.send(json.dumps(sub_msg))
        try:
            await asyncio.wait_for(_consume(ws, on_message), timeout=duration_sec)
        except asyncio.TimeoutError:
            return


async def _consume(ws, on_message) -> None:
    while True:
        raw = await ws.recv()
        try:
            data = json.loads(raw) if isinstance(raw, str) and raw.startswith("{") else {"raw": raw}
        except json.JSONDecodeError:
            data = {"raw": raw}
        result = on_message(data)
        if asyncio.iscoroutine(result):
            await result
