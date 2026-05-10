"""종목코드 정규화 — KRX 6자리 / yfinance 접미 / 미국 심볼 식별."""

from __future__ import annotations

import re

_KRX_RE = re.compile(r"^\d{6}$")
_KRX_YF_RE = re.compile(r"^(\d{6})\.K[SQ]$", re.IGNORECASE)
_US_SYM_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def is_korean(ticker: str) -> bool:
    """KRX 6자리 또는 005930.KS/.KQ 형식이면 True."""
    t = ticker.strip()
    return bool(_KRX_RE.match(t) or _KRX_YF_RE.match(t))


def is_us(ticker: str) -> bool:
    """대문자 1~10자리 알파넘 (NVDA, BRK.B, RDS-A 등)."""
    t = ticker.strip().upper()
    return not is_korean(t) and bool(_US_SYM_RE.match(t))


def to_krx(ticker: str) -> str:
    """6자리 KRX 코드로 변환. 예: '005930.KS' → '005930'."""
    t = ticker.strip()
    if _KRX_RE.match(t):
        return t
    m = _KRX_YF_RE.match(t)
    if m:
        return m.group(1)
    if t.isdigit():
        return t.zfill(6)
    raise ValueError(f"not a Korean ticker: {ticker!r}")


def to_yfinance(ticker: str, market: str = "KS") -> str:
    """KRX 6자리 → yfinance 접미 형식. 예: '005930' → '005930.KS'.

    market: 'KS' (KOSPI) 또는 'KQ' (KOSDAQ).
    """
    t = ticker.strip().upper()
    if _KRX_YF_RE.match(t):
        return t
    krx = to_krx(t)
    return f"{krx}.{market.upper()}"


def normalize(ticker: str) -> str:
    """공통 정규화: KRX는 6자리, US는 대문자."""
    t = ticker.strip()
    if is_korean(t):
        return to_krx(t)
    return t.upper()
