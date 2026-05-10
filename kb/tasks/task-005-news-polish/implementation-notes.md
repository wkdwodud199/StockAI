# 구현 노트 — task-005-news-polish

> Status: done
> Inputs: kb/tasks/task-005-news-polish/design.md
> Outputs: news_korean.py, ta_kis_patch.py 갱신, 7 tests
> Next step: task-006-websocket

## 설계 대비 변경 사항

| 항목 | 설계 | 실제 | 사유 |
|------|------|------|------|
| 종목명 lookup 소스 | KIS quote의 hts_kor_isnm | yfinance .KS info의 longName | KIS inquire-price 응답에는 종목명 필드가 없음 (업종명만 존재) |

## 구현 결정

1. **fallback 트리거** — 미국 티커가 들어오면 `AlphaVantageRateLimitError` raise. `route_to_vendor`의 fallback 체인이 자동으로 yfinance로 넘김.
2. **종목명 lookup 캐시** — `_NAME_CACHE: dict[str, str]`. Samsung Electronics 등 자주 쓰는 종목은 한 번만 yfinance 호출.
3. **Google News RSS** — 안정적인 공개 RSS. 네이버 금융 RSS는 비공식이라 회피.
4. **15건 제한** — 너무 많으면 LLM 토큰 낭비. 최근 7~14일 + 종목 검색이면 15건이면 충분.

## 발생한 이슈

- KIS quote 응답에 종목명 필드 부재 → yfinance .KS info로 우회.

## 테스트 결과

| 테스트 | 결과 |
|--------|------|
| normalize_ticker (3 형식) | pass |
| format_news_text (빈/채워짐) | pass |
| 미국 티커 fallback raise | pass |
| 005930 RSS fetch | pass (15건) |
| KOSPI 글로벌 뉴스 | pass |
| _build_query (yfinance lookup) | pass — Samsung Electronics 매핑 |

전체: 27/27 PASS (단위 12 + 어댑터 8 + 뉴스 7)

## 산출물

- `app/integrations/ta_dataflows/news_korean.py` (130 LOC)
- `app/integrations/ta_kis_patch.py` (4줄 추가, vendor 등록 + news_data 라우팅)
- `tests/test_news_korean.py` (60 LOC, 7 tests)
