"""한국어 뉴스 RSS dataflow — Google News RSS 기반.

KRX 종목 분석 시 한국어 뉴스가 필수. yfinance get_news는 영문/미국 위주라
TradingAgents의 news 분석가가 한국 종목에 대한 시그널을 받기 어렵다.

본 어댑터는 Google News RSS (한국어/한국 지역)를 사용해 종목명·티커 기반
검색을 수행하고 yfinance 호환 시그니처로 텍스트를 반환한다.

호환 시그니처:
- `get_news(ticker, curr_date, look_back_days=7) -> str`
- `get_global_news(curr_date, look_back_days=7) -> str`
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import quote

import requests

_KRX = re.compile(r"^\d{6}(?:\.K[SQ])?$", re.IGNORECASE)
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StockMtsTaBot/0.1)"}
_TIMEOUT = 10


def _normalize_ticker_for_search(ticker: str) -> str:
    """KRX 6자리 + .KS 형태 모두 6자리로."""
    t = ticker.strip().upper()
    m = re.match(r"^(\d{6})(?:\.K[SQ])?$", t)
    return m.group(1) if m else t


_NAME_CACHE: dict[str, str] = {}


def _ticker_name_lookup(ticker: str) -> str | None:
    """KRX 6자리 → 한국어 종목명. yfinance .KS info 기반. 실패 시 None.

    프로세스 내 캐시: 같은 ticker 반복 호출 시 yfinance 호출 안 함.
    """
    code = _normalize_ticker_for_search(ticker)
    if code in _NAME_CACHE:
        return _NAME_CACHE[code]
    try:
        import yfinance as yf
        for suffix in (".KS", ".KQ"):
            try:
                info = yf.Ticker(f"{code}{suffix}").info
            except Exception:
                continue
            name = info.get("longName") or info.get("shortName")
            if name:
                _NAME_CACHE[code] = name
                return name
    except Exception:
        pass
    return None


def _build_query(ticker: str) -> str:
    code = _normalize_ticker_for_search(ticker)
    name = _ticker_name_lookup(code)
    if name:
        return f'"{name}" OR "{code}"'
    return code


def _fetch_rss(query: str, *, hl: str = "ko", gl: str = "KR") -> list[dict]:
    url = (
        f"https://news.google.com/rss/search?q={quote(query)}"
        f"&hl={hl}&gl={gl}&ceid={gl}:{hl}"
    )
    resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
    if resp.status_code != 200:
        return []
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return []
    items = []
    for item in root.findall(".//item"):
        items.append(
            {
                "title": (item.findtext("title") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
                "pubDate": (item.findtext("pubDate") or "").strip(),
                "source": (item.findtext("source") or "").strip(),
            }
        )
    return items


def _filter_by_date(items: list[dict], cutoff: datetime) -> list[dict]:
    out = []
    for it in items:
        pub_str = it.get("pubDate", "")
        try:
            # RFC822: "Sun, 04 May 2026 09:30:00 GMT"
            pub_dt = datetime.strptime(pub_str, "%a, %d %b %Y %H:%M:%S %Z").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            try:
                pub_dt = datetime.strptime(pub_str[:25], "%a, %d %b %Y %H:%M:%S").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pub_dt = None  # type: ignore[assignment]
        if pub_dt is None or pub_dt >= cutoff:
            out.append(it)
    return out


def _format_news_text(query: str, items: list[dict], curr_date: str) -> str:
    if not items:
        return f"# Korean news for query '{query}' as of {curr_date}\n# (no items found)\n"
    lines = [
        f"# Korean news for query '{query}' as of {curr_date}",
        f"# Total items: {len(items)}",
        f"# Source: Google News RSS (hl=ko, gl=KR)",
        "",
    ]
    for i, it in enumerate(items, 1):
        lines.append(f"## {i}. {it['title']}")
        if it.get("source"):
            lines.append(f"- 출처: {it['source']}")
        if it.get("pubDate"):
            lines.append(f"- 게재: {it['pubDate']}")
        if it.get("link"):
            lines.append(f"- 링크: {it['link']}")
        lines.append("")
    return "\n".join(lines)


def get_news(
    ticker: Annotated[str, "ticker (KRX 6-digit, optionally .KS)"],
    curr_date: Annotated[str, "current date YYYY-MM-DD"] = "",
    look_back_days: Annotated[int, "days to look back"] = 7,
) -> str:
    """KRX 종목용 한국어 뉴스 텍스트 (yfinance get_news 시그니처 호환)."""
    if not _KRX.match(ticker.strip()):
        # 한국 티커가 아니면 빈 결과 (yfinance 폴백을 route_to_vendor가 처리)
        from tradingagents.dataflows.alpha_vantage_common import AlphaVantageRateLimitError
        raise AlphaVantageRateLimitError("not a Korean ticker; fallback")

    query = _build_query(ticker)
    items = _fetch_rss(query)
    if curr_date:
        try:
            cur = datetime.fromisoformat(curr_date).replace(tzinfo=timezone.utc)
            cutoff = cur - timedelta(days=look_back_days)
            items = _filter_by_date(items, cutoff)
        except ValueError:
            pass
    return _format_news_text(query, items[:15], curr_date or datetime.now().strftime("%Y-%m-%d"))


def get_global_news(
    curr_date: Annotated[str, "current date YYYY-MM-DD"] = "",
    look_back_days: Annotated[int, "days to look back"] = 7,
) -> str:
    """한국 시장 전반 매크로 뉴스."""
    items = _fetch_rss("KOSPI OR 코스피 OR 한국증시")
    if curr_date:
        try:
            cur = datetime.fromisoformat(curr_date).replace(tzinfo=timezone.utc)
            cutoff = cur - timedelta(days=look_back_days)
            items = _filter_by_date(items, cutoff)
        except ValueError:
            pass
    return _format_news_text("KOSPI / 한국증시", items[:15], curr_date or datetime.now().strftime("%Y-%m-%d"))
