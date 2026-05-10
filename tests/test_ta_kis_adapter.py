"""TradingAgents KIS 어댑터 단위·통합 테스트."""

from __future__ import annotations

import pytest


def test_patch_idempotent() -> None:
    from app.integrations.ta_kis_patch import enable_kis_for_korean_tickers, is_applied

    enable_kis_for_korean_tickers()
    enable_kis_for_korean_tickers()  # 두 번 호출해도 안전
    assert is_applied()


def test_patch_registers_kis_vendor() -> None:
    from app.integrations.ta_kis_patch import enable_kis_for_korean_tickers

    enable_kis_for_korean_tickers()
    from tradingagents.dataflows.interface import VENDOR_LIST, VENDOR_METHODS

    assert "kis" in VENDOR_LIST
    assert "kis" in VENDOR_METHODS["get_stock_data"]
    assert "kis" in VENDOR_METHODS["get_indicators"]


def test_data_vendors_routed_to_kis_first() -> None:
    from app.integrations.ta_kis_patch import enable_kis_for_korean_tickers

    enable_kis_for_korean_tickers()
    from tradingagents.dataflows.config import get_config

    dv = get_config()["data_vendors"]
    assert dv["core_stock_apis"].split(",")[0] == "kis"
    assert dv["technical_indicators"].split(",")[0] == "kis"


def test_kis_get_stock_data_us_ticker_raises_for_fallback() -> None:
    """비한국 티커는 AlphaVantageRateLimitError raise → route_to_vendor가 yfinance로 폴백 (회귀: collab.md High 1)."""
    from app.integrations.ta_kis_patch import enable_kis_for_korean_tickers
    from tradingagents.dataflows.alpha_vantage_common import AlphaVantageRateLimitError

    enable_kis_for_korean_tickers()
    from app.integrations.ta_dataflows.kis_api import _to_krx_code

    with pytest.raises(AlphaVantageRateLimitError):
        _to_krx_code("NVDA")
    with pytest.raises(AlphaVantageRateLimitError):
        _to_krx_code("AAPL")


def test_yfinance_wrap_adds_ks_for_krx() -> None:
    from app.integrations.ta_kis_patch import _maybe_add_ks

    assert _maybe_add_ks("005930") == "005930.KS"
    assert _maybe_add_ks("005930.KS") == "005930.KS"
    assert _maybe_add_ks("NVDA") == "NVDA"
    assert _maybe_add_ks("BRK.B") == "BRK.B"


def test_llm_config_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.integrations.ta_runner import _resolve_llm_config

    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("TA_DEEP_LLM", raising=False)
    cfg = _resolve_llm_config()
    assert cfg.provider == "anthropic"
    assert cfg.deep_model.startswith("claude-")

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    cfg = _resolve_llm_config()
    assert cfg.provider == "openai"
    assert cfg.deep_model.startswith("gpt-")

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    cfg = _resolve_llm_config()
    assert cfg.provider == "ollama"
    assert cfg.backend_url is not None

    monkeypatch.setenv("LLM_PROVIDER", "unknown_provider")
    with pytest.raises(ValueError):
        _resolve_llm_config()


@pytest.mark.network
def test_kis_get_stock_data_returns_csv() -> None:
    from app.integrations.ta_kis_patch import enable_kis_for_korean_tickers
    enable_kis_for_korean_tickers()
    from tradingagents.dataflows.interface import route_to_vendor

    csv = route_to_vendor("get_stock_data", "005930", "2026-04-25", "2026-05-09")
    assert "Date,Open,High,Low,Close,Volume" in csv
    assert csv.count("\n") > 5  # 헤더 + 최소 몇 줄 데이터


@pytest.mark.network
def test_kis_get_stock_data_handles_yf_suffix() -> None:
    from app.integrations.ta_kis_patch import enable_kis_for_korean_tickers
    enable_kis_for_korean_tickers()
    from tradingagents.dataflows.interface import route_to_vendor

    csv = route_to_vendor("get_stock_data", "005930.KS", "2026-04-25", "2026-05-09")
    assert "Date,Open,High,Low,Close,Volume" in csv


@pytest.mark.network
def test_kis_indicators_returns_text() -> None:
    from app.integrations.ta_kis_patch import enable_kis_for_korean_tickers
    enable_kis_for_korean_tickers()
    from tradingagents.dataflows.interface import route_to_vendor

    out = route_to_vendor(
        "get_indicators", "005930", "close_50_sma", "2026-05-09", 5
    )
    assert "close_50_sma" in out
    assert "005930" in out
