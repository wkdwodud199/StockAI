"""모의 환경 통합 스모크 — pytest 마커 `network` 필요.

실행:
    .venv\\Scripts\\python.exe -m pytest tests/smoke_kis_mock.py -m network -v

주의:
- 실제 KIS 모의 서버에 호출됨 (네트워크 필요)
- 매수/매도는 장중 시간(09:00~15:30 KST)에만 통과 — 그 외 시간에는 자동 skip
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

try:
    from zoneinfo import ZoneInfo
    _KST = ZoneInfo("Asia/Seoul")
except ImportError:  # pragma: no cover
    _KST = None

from app.kis.account import inquire_balance_domestic
from app.kis.auth import get_access_token
from app.kis.config import KisEnvironment
from app.kis.quote_domestic import current_price, daily_candles, orderbook

ENV = KisEnvironment.MOCK_DOMESTIC


def _is_market_hours() -> bool:
    if _KST is None:
        return False
    now = datetime.now(_KST)
    if now.weekday() >= 5:
        return False
    if now.hour < 9 or now.hour > 15:
        return False
    if now.hour == 15 and now.minute > 30:
        return False
    return True


@pytest.mark.network
def test_token_issuance() -> None:
    token = get_access_token(ENV)
    assert isinstance(token, str)
    assert len(token) > 50


@pytest.mark.network
def test_current_price_005930() -> None:
    q = current_price("005930", env=ENV)
    assert q.ticker == "005930"
    assert q.price > 0


@pytest.mark.network
def test_daily_candles() -> None:
    end = date.today()
    candles = daily_candles("005930", end - timedelta(days=14), end, env=ENV)
    assert len(candles) > 0
    assert all(c.close > 0 for c in candles)


@pytest.mark.network
def test_orderbook() -> None:
    ob = orderbook("005930", env=ENV)
    assert ob.ticker == "005930"


@pytest.mark.network
def test_account_balance() -> None:
    summary = inquire_balance_domestic(env=ENV)
    assert summary.deposit >= 0


@pytest.mark.network
@pytest.mark.market_hours
def test_buy_sell_roundtrip() -> None:
    """장중 시간(09:00~15:30 KST 평일)에만 통과. 그 외엔 자동 skip."""
    if not _is_market_hours():
        pytest.skip("장외 시간 — 매매 라운드트립 skip")
    from app.kis.order_domestic import buy, sell
    q = current_price("005930", env=ENV)
    r = buy("005930", qty=1, price=q.price, env=ENV)
    assert r.success
    assert r.order_no
    s = sell("005930", qty=1, price=q.price, env=ENV)
    assert s.success
