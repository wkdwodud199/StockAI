# 설계 문서 — task-005-news-polish (한국어 뉴스 RSS + 정리)

> Status: done
> Inputs: kb/tasks/task-003-ta-adapter/, app/integrations/ta_kis_patch.py
> Outputs: app/integrations/ta_dataflows/news_korean.py, ta_kis_patch.py 갱신, tests/test_news_korean.py
> Next step: task-006-websocket (실시간 시세)

## 목표 (Objective)

KRX 종목 분석 시 영어 뉴스만으로는 시그널이 부족하므로, Google News RSS(한국어/한국 지역) 어댑터를 추가해 TradingAgents news 분석가가 한국 종목 기사를 받을 수 있게 한다.

## 범위 (Scope)

- 포함: news_korean.py (get_news + get_global_news), ta_kis_patch에서 KIS 벤더로 등록, yfinance .KS info를 이용한 종목명 lookup + 캐시
- 제외: 네이버 금융 직접 RSS (불안정), 뉴스 본문 크롤링, 감정 점수 자동 산출

## 제약 (Constraints)

- KRX 6자리(또는 .KS) 티커일 때만 동작. 그 외엔 `AlphaVantageRateLimitError` raise → route_to_vendor가 yfinance로 자동 폴백
- 네트워크 호출 ≤2회 (RSS fetch + 종목명 lookup yfinance — 캐시 후 0회)
- 종목명 캐시는 프로세스 메모리 (Streamlit 재시작 시 리셋)

## 구현 단계

1. `news_korean.py` — RSS fetch + 날짜 필터 + 텍스트 포맷
2. yfinance .KS info에서 longName/shortName 추출
3. ta_kis_patch에 등록 + `data_vendors["news_data"] = "kis,yfinance"`
4. 단위 + 네트워크 테스트 7건

## 파일/모듈 영향

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `app/integrations/ta_dataflows/news_korean.py` | create | 한국어 뉴스 RSS 어댑터 |
| `app/integrations/ta_kis_patch.py` | modify | get_news/get_global_news 벤더 등록 + news_data 라우팅 |
| `tests/test_news_korean.py` | create | 7 tests |

## 테스트 기준

- [x] _normalize_ticker 005930 / 005930.KS / NVDA 정상 변환
- [x] _format_news_text 빈 / 채워진 케이스 모두 정상
- [x] 미국 티커 (NVDA) → AlphaVantageRateLimitError raise
- [x] get_news("005930") → "Korean news" 헤더 + 기사
- [x] get_global_news → KOSPI 매크로 뉴스
- [x] _build_query("005930") → "Samsung Electronics Co., Ltd." OR "005930"

## 오픈 이슈

- Google News RSS는 한 번에 ~100건, 본 어댑터는 15건 제한
- 종목명 캐시는 프로세스 단위 — 멀티 프로세스에서 각자 yfinance 호출
- RSS 응답 콘솔 mojibake 가능 (cp949 한계, 데이터는 UTF-8 정상)
