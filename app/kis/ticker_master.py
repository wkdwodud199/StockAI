"""KRX 종목 마스터 — pykrx 기반.

종목코드 ↔ 종목명 매핑을 디스크에 캐시하여 빠른 검색 제공.
캐시는 24시간 유효 (KRX 신규/상폐 반영용).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from app.kis.utils_paths import KIS_CACHE_DIR

_MASTER_PATH = KIS_CACHE_DIR / "ticker_master.json"
_TTL_SEC = 24 * 3600


@dataclass(frozen=True)
class Ticker:
    code: str  # 6자리
    name: str  # 한국어 종목명
    market: str  # 'KOSPI' | 'KOSDAQ'

    def to_dict(self) -> dict:
        return asdict(self)


def _fetch_all_tickers() -> list[Ticker]:
    """FinanceDataReader 로 KOSPI + KOSDAQ 전체 종목 마스터 fetch."""
    import FinanceDataReader as fdr

    tickers: list[Ticker] = []
    for market_label in ("KOSPI", "KOSDAQ"):
        df = fdr.StockListing(market_label)
        # 컬럼: Code, Name, Market, ... (FDR 0.9 기준)
        code_col = "Code" if "Code" in df.columns else "Symbol"
        name_col = "Name"
        if name_col not in df.columns or code_col not in df.columns:
            continue
        for _, row in df.iterrows():
            code = str(row[code_col]).strip().zfill(6)
            name = str(row[name_col]).strip()
            if code and name and len(code) == 6 and code.isdigit():
                tickers.append(Ticker(code=code, name=name, market=market_label))
    return tickers


def _load_cache() -> list[Ticker] | None:
    if not _MASTER_PATH.exists():
        return None
    try:
        raw = json.loads(_MASTER_PATH.read_text(encoding="utf-8"))
        if time.time() - raw.get("ts", 0) > _TTL_SEC:
            return None
        return [Ticker(**t) for t in raw.get("tickers", [])]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _save_cache(tickers: list[Ticker]) -> None:
    KIS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _MASTER_PATH.write_text(
        json.dumps(
            {"ts": time.time(), "tickers": [t.to_dict() for t in tickers]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


_CACHE: list[Ticker] | None = None


def get_all_tickers(*, force_refresh: bool = False) -> list[Ticker]:
    """전체 종목 마스터 (메모리 캐시 + 디스크 캐시)."""
    global _CACHE
    if _CACHE is not None and not force_refresh:
        return _CACHE

    if not force_refresh:
        cached = _load_cache()
        if cached is not None:
            _CACHE = cached
            return _CACHE

    tickers = _fetch_all_tickers()
    _save_cache(tickers)
    _CACHE = tickers
    return _CACHE


def search(query: str, *, limit: int = 20) -> list[Ticker]:
    """종목코드 또는 종목명 부분일치 검색.

    - 코드로 검색: '005' → 005xxx 시작 코드
    - 이름으로 검색: '삼성' → '삼성전자', '삼성SDI', ...
    - 빈 query: 빈 결과
    """
    q = (query or "").strip()
    if not q:
        return []
    all_tickers = get_all_tickers()
    q_lower = q.lower()

    # 정확 코드 매치 우선
    exact_code = [t for t in all_tickers if t.code == q]
    if exact_code:
        return exact_code[:limit]

    # 이름 시작 매치 우선
    name_starts = [t for t in all_tickers if t.name.lower().startswith(q_lower)]
    # 이름 포함 매치
    name_contains = [
        t for t in all_tickers
        if q_lower in t.name.lower() and not t.name.lower().startswith(q_lower)
    ]
    # 코드 시작 매치 (숫자 query)
    code_starts = (
        [t for t in all_tickers if t.code.startswith(q)] if q.isdigit() else []
    )

    combined: list[Ticker] = []
    seen = set()
    for batch in (name_starts, name_contains, code_starts):
        for t in batch:
            if t.code not in seen:
                combined.append(t)
                seen.add(t.code)
                if len(combined) >= limit:
                    return combined
    return combined


def lookup_name(code: str) -> str | None:
    """종목코드 → 종목명. 캐시 hit."""
    code = (code or "").strip()
    if not code:
        return None
    for t in get_all_tickers():
        if t.code == code:
            return t.name
    return None
