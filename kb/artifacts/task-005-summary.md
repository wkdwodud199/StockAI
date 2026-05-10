# 산출물 요약 — task-005-news-polish

> Status: done
> Inputs: kb/tasks/task-005-news-polish/implementation-notes.md
> Outputs: 본 요약 + task-006 진입 신호
> Next step: task-006-websocket (실시간 시세)

## 작업 요약

- **Task ID**: task-005-news-polish
- **제목**: 한국어 뉴스 RSS dataflow (Google News)
- **완료일**: 2026-05-10

## 산출물

| 산출물 | 경로 | 설명 |
|--------|------|------|
| 한국어 뉴스 RSS 어댑터 | `app/integrations/ta_dataflows/news_korean.py` | get_news + get_global_news, yfinance .KS 종목명 lookup |
| 패치 갱신 | `app/integrations/ta_kis_patch.py` | get_news/get_global_news 벤더 등록 + `data_vendors["news_data"] = "kis,yfinance"` |
| 테스트 | `tests/test_news_korean.py` | 7 tests (3 unit + 3 network + 1 integration) |

## 주요 결정

- **fallback 트리거 패턴** — 미국 티커는 `AlphaVantageRateLimitError` raise → route_to_vendor가 yfinance로 자동 폴백.
- **종목명 캐시** — 프로세스 내 dict 메모이제이션. yfinance 호출 1회 후 재사용.
- **Google News RSS** — 비공식 네이버 금융 RSS 회피, 안정적인 공개 RSS 사용.

## 검증

```
$ python -c "from app.integrations.ta_dataflows.news_korean import _build_query; print(_build_query('005930'))"
"Samsung Electronics Co., Ltd." OR "005930"

$ python -m pytest tests
27 passed in 4.35s
```

## 관련 문서

- 설계: `kb/tasks/task-005-news-polish/design.md`
- 구현 노트: `kb/tasks/task-005-news-polish/implementation-notes.md`
