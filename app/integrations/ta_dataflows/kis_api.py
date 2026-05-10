"""KIS Open API → TradingAgents dataflow 어댑터.

호환 시그니처 (yfinance dataflow 함수와 동일):
- `get_stock_data(symbol, start_date, end_date) -> str` (CSV 텍스트)
- `get_stockstats_indicators_window(symbol, indicator, curr_date, look_back_days) -> str`

본 모듈은 `app/integrations/ta_dataflows/`에 위치하고, `ta_kis_patch.py`가
TradingAgents의 `interface.VENDOR_METHODS`에 import-time으로 등록한다.
TradingAgents 저장소 코드는 단 한 줄도 수정하지 않는다.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated

import pandas as pd

from .kis_config import DEFAULT_KIS_ENV_NAME, ensure_cache_dir

_KRX_BARE = re.compile(r"^\d{6}$")
_KRX_YF = re.compile(r"^(\d{6})\.K[SQ]$", re.IGNORECASE)


def _to_krx_code(symbol: str) -> str:
    s = symbol.strip().upper()
    if _KRX_BARE.match(s):
        return s
    m = _KRX_YF.match(s)
    if m:
        return m.group(1)
    raise ValueError(f"not a Korean ticker: {symbol!r}")


def is_korean_ticker(symbol: str) -> bool:
    s = symbol.strip().upper()
    return bool(_KRX_BARE.match(s) or _KRX_YF.match(s))


def _kis_env():
    """app.kis 모듈을 lazy-load (TradingAgents가 단독 사용될 때 import 실패 방지)."""
    from app.kis.config import KisEnvironment, parse_env

    return parse_env(DEFAULT_KIS_ENV_NAME)


def _fetch_candles_df(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """KIS 일봉 → DataFrame (Date, Open, High, Low, Close, Volume)."""
    from app.kis.quote_domestic import daily_candles

    code = _to_krx_code(symbol)
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    candles = daily_candles(code, start, end, env=_kis_env())
    rows = [
        {
            "Date": c.date.isoformat(),
            "Open": c.open,
            "High": c.high,
            "Low": c.low,
            "Close": c.close,
            "Volume": c.volume,
        }
        for c in candles
    ]
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Date").reset_index(drop=True)
    return df


def _cache_path(symbol: str, start_date: str, end_date: str) -> "pathlib.Path":
    code = _to_krx_code(symbol)
    return ensure_cache_dir() / f"{code}_{start_date}_{end_date}.csv"


def get_stock_data(
    symbol: Annotated[str, "ticker symbol (KRX 6-digit, e.g., 005930 or 005930.KS)"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """KIS 일봉 → CSV 문자열 (yfinance get_YFin_data_online과 동일 포맷)."""
    # 형식 검증 (yfinance와 동일하게 strptime)
    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")

    code = _to_krx_code(symbol)
    cache = _cache_path(code, start_date, end_date)

    if cache.exists():
        df = pd.read_csv(cache)
    else:
        df = _fetch_candles_df(code, start_date, end_date)
        if df.empty:
            return f"No data found for symbol '{symbol}' between {start_date} and {end_date}"
        df.to_csv(cache, index=False)

    # 숫자 컬럼 반올림 (yfinance와 동일)
    for col in ("Open", "High", "Low", "Close"):
        if col in df.columns:
            df[col] = df[col].round(2)

    csv_string = df.to_csv(index=False)
    header = (
        f"# Stock data for {code} (KIS) from {start_date} to {end_date}\n"
        f"# Total records: {len(df)}\n"
        f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )
    return header + csv_string


def _stockstats_indicators_dict(symbol: str, indicator: str, curr_date: str) -> dict[str, str]:
    """주어진 심볼·지표를 ~3년치 일봉으로 stockstats 계산해 {date: value} dict 반환."""
    from stockstats import wrap

    end_dt = pd.to_datetime(curr_date)
    start_dt = end_dt - pd.DateOffset(years=3)
    df = _fetch_candles_df(symbol, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
    if df.empty:
        return {}

    # stockstats 는 소문자 컬럼 기대
    df = df.rename(columns={c: c.lower() for c in df.columns})
    df["date"] = pd.to_datetime(df["date"])
    # date를 보존하기 위해 별도 시리즈로 저장 (stockstats가 컬럼을 소비할 수 있음)
    date_series = df["date"].copy()
    sdf = wrap(df.copy())
    _ = sdf[indicator]  # trigger calc

    # sdf 길이/인덱스가 원본과 동일하다고 가정
    out: dict[str, str] = {}
    for i, val in enumerate(sdf[indicator].tolist()):
        if i >= len(date_series):
            break
        d = date_series.iloc[i]
        ds = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
        out[ds] = "N/A" if pd.isna(val) else str(val)
    return out


# 인디케이터 설명 (yfinance 모듈의 best_ind_params와 동일 키)
_IND_DESC = {
    "close_50_sma": "50 SMA: medium-term trend",
    "close_200_sma": "200 SMA: long-term trend benchmark",
    "close_10_ema": "10 EMA: responsive short-term average",
    "macd": "MACD: momentum via EMA differences",
    "macds": "MACD Signal: smoothing of MACD line",
    "macdh": "MACD Histogram: gap between MACD and signal",
    "rsi": "RSI: 70/30 thresholds for overbought/oversold",
    "boll": "Bollinger Middle: 20 SMA basis",
    "boll_ub": "Bollinger Upper Band",
    "boll_lb": "Bollinger Lower Band",
    "atr": "ATR: average true range volatility",
    "vwma": "VWMA: volume-weighted moving average",
    "mfi": "MFI: money flow index",
}


def get_stockstats_indicators_window(
    symbol: Annotated[str, "KRX ticker (6-digit or .KS)"],
    indicator: Annotated[str, "technical indicator (e.g., close_50_sma)"],
    curr_date: Annotated[str, "current trading date YYYY-MM-DD"],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:
    if indicator not in _IND_DESC:
        raise ValueError(f"Indicator {indicator} not supported. choices: {list(_IND_DESC)}")

    end_dt = pd.to_datetime(curr_date)
    start_dt = end_dt - pd.DateOffset(days=look_back_days)
    code = _to_krx_code(symbol)
    values = _stockstats_indicators_dict(code, indicator, curr_date)

    lines: list[str] = []
    cur = end_dt
    while cur >= start_dt:
        ds = cur.strftime("%Y-%m-%d")
        v = values.get(ds, "N/A: Not a trading day (weekend or holiday)")
        lines.append(f"{ds}: {v}")
        cur -= pd.Timedelta(days=1)
    body = "\n".join(lines)

    return (
        f"## {indicator} values for {code} (KIS) from "
        f"{start_dt:%Y-%m-%d} to {end_dt:%Y-%m-%d}:\n\n"
        + body
        + "\n\n"
        + _IND_DESC[indicator]
    )
