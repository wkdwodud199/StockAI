"""TradingAgents에 KIS dataflow를 import-time으로 주입.

호출 시:
- `interface.VENDOR_LIST`에 'kis' 추가
- `interface.VENDOR_METHODS['get_stock_data']['kis']` 등록
- `interface.VENDOR_METHODS['get_indicators']['kis']` 등록
- `set_config({"data_vendors": {core_stock_apis: 'kis,yfinance', ...}})` — KIS 우선, yfinance 폴백
- yfinance 모듈 함수에 KRX 티커 자동 .KS 부착 monkey-patch

idempotent: 여러 번 호출되어도 안전.
"""

from __future__ import annotations

import functools
import re
from threading import Lock

_LOCK = Lock()
_APPLIED = False

_KRX_BARE = re.compile(r"^\d{6}$")


def _has_ks_suffix(s: str) -> bool:
    return s.upper().endswith((".KS", ".KQ"))


def _maybe_add_ks(symbol: str) -> str:
    """6자리 KRX 코드면 .KS 부착. 그 외엔 그대로."""
    s = (symbol or "").strip()
    if _KRX_BARE.match(s) and not _has_ks_suffix(s):
        return f"{s}.KS"
    return s


def _wrap_yf_callable(func):
    """첫 인자(symbol/ticker)에 한국 티커가 들어오면 .KS 자동 부착."""

    @functools.wraps(func)
    def wrapper(symbol_or_ticker, *args, **kwargs):
        return func(_maybe_add_ks(symbol_or_ticker), *args, **kwargs)

    wrapper.__wrapped__ = func  # type: ignore[attr-defined]
    return wrapper


def enable_kis_for_korean_tickers() -> None:
    """TradingAgents에 KIS 어댑터를 등록한다 (1회만 적용)."""
    global _APPLIED
    with _LOCK:
        if _APPLIED:
            return
        _do_apply()
        _APPLIED = True


def is_applied() -> bool:
    return _APPLIED


def _do_apply() -> None:
    from tradingagents.dataflows import interface, y_finance, yfinance_news
    from tradingagents.dataflows.config import set_config, get_config
    from app.integrations.ta_dataflows import kis_api

    # 1) Vendor 등록
    if "kis" not in interface.VENDOR_LIST:
        interface.VENDOR_LIST.append("kis")
    interface.VENDOR_METHODS.setdefault("get_stock_data", {})["kis"] = kis_api.get_stock_data
    interface.VENDOR_METHODS.setdefault("get_indicators", {})["kis"] = (
        kis_api.get_stockstats_indicators_window
    )

    # 2) yfinance 함수에 KRX → .KS 자동 부착 monkey-patch
    yf_targets = [
        ("get_YFin_data_online", y_finance),
        ("get_stock_stats_indicators_window", y_finance),
        ("get_stockstats_indicator", y_finance),
        ("get_fundamentals", y_finance),
        ("get_balance_sheet", y_finance),
        ("get_cashflow", y_finance),
        ("get_income_statement", y_finance),
        ("get_insider_transactions", y_finance),
        ("get_news_yfinance", yfinance_news),
        ("get_global_news_yfinance", yfinance_news),
    ]
    for name, mod in yf_targets:
        orig = getattr(mod, name, None)
        if orig is None or getattr(orig, "__wrapped__", None) is not None:
            continue  # 이미 wrap 되었거나 없음
        setattr(mod, name, _wrap_yf_callable(orig))

    # interface.py 가 import 시점에 직접 가져온 참조도 갱신
    for name, _ in yf_targets:
        if hasattr(interface, name):
            setattr(interface, name, getattr(_module_for_name(name), name))

    # VENDOR_METHODS에 등록된 yfinance 콜러블도 새 wrap된 함수로 교체
    interface.VENDOR_METHODS.setdefault("get_stock_data", {})["yfinance"] = (
        y_finance.get_YFin_data_online
    )
    interface.VENDOR_METHODS.setdefault("get_indicators", {})["yfinance"] = (
        y_finance.get_stock_stats_indicators_window
    )
    for fn in (
        "get_fundamentals", "get_balance_sheet", "get_cashflow", "get_income_statement",
        "get_insider_transactions",
    ):
        if fn in interface.VENDOR_METHODS:
            interface.VENDOR_METHODS[fn]["yfinance"] = getattr(y_finance, fn)
    if "get_news" in interface.VENDOR_METHODS:
        interface.VENDOR_METHODS["get_news"]["yfinance"] = yfinance_news.get_news_yfinance
    if "get_global_news" in interface.VENDOR_METHODS:
        interface.VENDOR_METHODS["get_global_news"]["yfinance"] = (
            yfinance_news.get_global_news_yfinance
        )

    # 3) Vendor 우선순위 설정 — KIS first, yfinance fallback
    cfg = get_config()
    data_vendors = dict(cfg.get("data_vendors", {}))
    data_vendors["core_stock_apis"] = "kis,yfinance"
    data_vendors["technical_indicators"] = "kis,yfinance"
    # fundamental_data, news_data는 yfinance에서 .KS 폴백 처리
    data_vendors.setdefault("fundamental_data", "yfinance")
    data_vendors.setdefault("news_data", "yfinance")
    set_config({"data_vendors": data_vendors})


def _module_for_name(func_name: str):
    """함수 이름 → 보유 모듈 (interface 갱신용)."""
    from tradingagents.dataflows import y_finance, yfinance_news

    if func_name in {"get_news_yfinance", "get_global_news_yfinance"}:
        return yfinance_news
    return y_finance
