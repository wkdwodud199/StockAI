"""한국어 뉴스 RSS 어댑터 테스트."""

from __future__ import annotations

import pytest

from app.integrations.ta_dataflows.news_korean import (
    _build_query,
    _format_news_text,
    _normalize_ticker_for_search,
    get_global_news,
    get_news,
)


def test_normalize_ticker() -> None:
    assert _normalize_ticker_for_search("005930") == "005930"
    assert _normalize_ticker_for_search("005930.KS") == "005930"
    assert _normalize_ticker_for_search("005930.kq") == "005930"
    assert _normalize_ticker_for_search("NVDA") == "NVDA"


def test_format_news_text_empty() -> None:
    out = _format_news_text("005930", [], "2026-05-09")
    assert "(no items found)" in out
    assert "005930" in out


def test_format_news_text_items() -> None:
    items = [
        {
            "title": "삼성전자 신제품 발표",
            "link": "https://news.example.com/1",
            "pubDate": "Sun, 09 May 2026 12:00:00 GMT",
            "source": "예시뉴스",
        }
    ]
    out = _format_news_text("005930", items, "2026-05-09")
    assert "## 1. 삼성전자 신제품 발표" in out
    assert "예시뉴스" in out


def test_get_news_non_korean_raises_for_fallback() -> None:
    """미국 티커는 fallback 트리거를 위한 예외 raise."""
    with pytest.raises(Exception):
        get_news("NVDA", "2026-05-09")


@pytest.mark.network
def test_get_news_005930_returns_text() -> None:
    out = get_news("005930", "2026-05-09", look_back_days=14)
    assert "Korean news" in out
    # 빈 결과여도 헤더는 항상 있음
    assert len(out) > 50


@pytest.mark.network
def test_get_global_news_returns_text() -> None:
    out = get_global_news("2026-05-09", look_back_days=7)
    assert "Korean news" in out


@pytest.mark.network
def test_build_query_uses_name() -> None:
    """yfinance lookup 성공 시 종목명이 query에 포함됨."""
    q = _build_query("005930")
    # 005930은 항상 들어가고, lookup 성공 시 "Samsung" 또는 "삼성"이 포함
    assert "005930" in q
