# 설계 문서 — task-003-ta-adapter (TradingAgents KIS 데이터플로우 어댑터)

> Status: ready
> Inputs: kb/tasks/task-002-kis-client/ (완료), TradingAgents/tradingagents/dataflows/{interface,y_finance,config}.py, default_config.py, graph/trading_graph.py
> Outputs: TradingAgents/tradingagents/dataflows/kis_api.py + kis_config.py, app/integrations/ta_kis_patch.py + ta_runner.py, KRX 종목으로 propagate() 동작 확인
> Next step: task-004-streamlit-ui — UI에서 ta_runner.run_analysis() 노출

## 목표 (Objective)

TauricResearch/TradingAgents를 **포크하지 않고** 한국주식(KRX 6자리 코드)을 분석할 수 있도록 import-time 패치 모듈을 만든다. 미국 종목은 yfinance 그대로, 한국 종목은 KIS API + (뉴스/펀더멘털은 yfinance .KS 폴백)으로 라우팅한다.

## 범위 (Scope)

- 포함:
  - `dataflows/kis_api.py` — `get_stock_data`, `get_stockstats_indicators_window` 시그니처 호환 함수 (CSV 문자열 반환)
  - `dataflows/kis_config.py` — KIS dataflow가 사용할 KisEnvironment 기본값 (모의 국내)
  - `app/integrations/ta_kis_patch.py` — `interface.VENDOR_LIST` + `VENDOR_METHODS`에 `"kis"` 등록 + `set_config({"data_vendors": {...}})` 헬퍼 + 한국 티커 자동 감지 시 yfinance 호출에 `.KS` 자동 부착
  - `app/integrations/ta_runner.py` — `run_analysis(ticker, date)` / `run_analysis_streaming(ticker, date)` + LLM_PROVIDER 환경변수에서 provider/model 결정
  - 단순 통합 테스트: KIS 어댑터의 stock_data/indicators가 CSV 형태 문자열 반환
- 제외:
  - 한국어 뉴스 RSS 통합 (Phase D 후속 task)
  - KIS 기반 fundamentals 직접 구현 (yfinance .KS 폴백으로 충분)
  - propagate() 전체 LLM 파이프라인 자동 테스트 (LLM 비용·시간 부담 — Streamlit에서 사용자 트리거 시 검증)

## 제약 (Constraints)

- TradingAgents 코어 코드 수정 금지 (`dataflows/`에 새 파일만 추가, `interface.py`는 import-time monkey-patch)
- 어댑터 함수는 `y_finance.py` 함수와 동일 시그니처/리턴 타입 (str). 호출자(agents)는 어떤 벤더든 모름
- LLM_PROVIDER 환경변수: `anthropic`(기본) | `openai` | `ollama`. 미설정 시 `anthropic`으로 기본
- 모델명도 환경변수로 오버라이드 가능: `TA_DEEP_LLM`, `TA_QUICK_LLM`. 미설정 시 provider별 합리적 기본
- KIS 호출은 모의 환경 (`MOCK_DOMESTIC`)을 사용 — 시세는 실전·모의 동일 데이터, 토큰만 모의 키
- 한국 티커 정규화는 `app/utils/ticker.py`의 `is_korean`/`to_krx`/`to_yfinance` 사용

## 구현 단계 (Implementation Steps)

1. `TradingAgents/tradingagents/dataflows/kis_config.py` — KIS dataflow가 사용할 환경(`MOCK_DOMESTIC`) + 데이터 캐시 디렉토리 상수
2. `TradingAgents/tradingagents/dataflows/kis_api.py` —
   - `get_stock_data(symbol, start_date, end_date) -> str` : KRX 6자리(또는 .KS) → KIS daily_candles → yfinance 호환 CSV 텍스트 (Date,Open,High,Low,Close,Volume + 헤더 코멘트)
   - `get_stockstats_indicators_window(symbol, indicator, curr_date, look_back_days) -> str` : KIS 일봉을 stockstats `wrap()`에 넣어 지표 계산 후 yfinance 함수와 동일 출력 포맷
   - 내부 캐시: `~/.kis_cache/ta_csv/<symbol>_<start>_<end>.csv` (재호출 시 디스크 hit)
3. `app/integrations/ta_kis_patch.py` —
   - `enable_kis_for_korean_tickers()` 함수 1개. 호출 시:
     - `interface.VENDOR_LIST`에 `"kis"` 추가
     - `interface.VENDOR_METHODS["get_stock_data"]["kis"] = kis_api.get_stock_data`
     - `interface.VENDOR_METHODS["get_indicators"]["kis"] = kis_api.get_stockstats_indicators_window`
     - `set_config({"data_vendors": {"core_stock_apis": "kis,yfinance", "technical_indicators": "kis,yfinance", ...}})` (fallback 체인)
     - yfinance 함수 monkey-patch: 입력이 KRX 6자리면 `.KS` 부착 후 호출
   - 한 번만 호출되도록 idempotent guard
4. `app/integrations/ta_runner.py` —
   - `_resolve_llm_config()` : LLM_PROVIDER 환경변수 → (provider, deep_model, quick_model, backend_url) 결정
     - anthropic: claude-sonnet-4-5 / claude-haiku-4-5
     - openai: gpt-5.2-chat-latest 둘 다
     - ollama: qwen2.5 / llama3.2
   - `_make_config()` : DEFAULT_CONFIG 복사 + LLM 오버라이드
   - `run_analysis(ticker, date_str, debug=False) -> dict` :
     - `enable_kis_for_korean_tickers()` 호출
     - `TradingAgentsGraph(config=_make_config())` 생성
     - `propagate(ticker, date_str)` 호출
     - 결과를 `{rating, action, summary, market_report, news_report, fundamentals_report, sentiment_report, investment_plan, trader_plan, final_decision}` dict로 정규화 반환
   - `run_analysis_streaming(...) -> Iterator[dict]` (debug=True 시 chunk별 yield) — Streamlit `st.write_stream`용
5. `tests/test_ta_kis_adapter.py` — KIS 어댑터 단위 테스트
   - get_stock_data로 005930 호출 → CSV 헤더 + 데이터 라인 ≥1 검증
   - get_stockstats_indicators_window로 005930 close_50_sma 호출 → "## close_50_sma values from..." 형식 확인
   - 한국 티커 6자리 + .KS 둘 다 동작
6. (verify only — 자동 테스트 X) `python -c "from app.integrations.ta_runner import enable_kis_only; enable_kis_only()"` 후 어댑터가 등록되었는지 확인

## 파일/모듈 영향 (Affected Files/Modules)

| 파일/모듈 | 변경 유형 | 설명 |
|-----------|-----------|------|
| `TradingAgents/tradingagents/dataflows/kis_api.py` | create | KIS 기반 stock_data + indicators (CSV/stockstats 출력) |
| `TradingAgents/tradingagents/dataflows/kis_config.py` | create | KIS dataflow 설정 상수 |
| `app/integrations/ta_kis_patch.py` | create | import-time monkey-patch + VENDOR 등록 + set_config |
| `app/integrations/ta_runner.py` | create | LLM 라우팅 + propagate 래퍼 + 결과 정규화 |
| `tests/test_ta_kis_adapter.py` | create | 어댑터 단위 테스트 (network 마커) |
| `app/utils/ticker.py` | already exists | 패치에서 사용 |

## 테스트 기준 (Test Criteria)

- [x] `python -c "from app.integrations.ta_kis_patch import enable_kis_for_korean_tickers; enable_kis_for_korean_tickers(); from tradingagents.dataflows.interface import VENDOR_LIST, VENDOR_METHODS; assert 'kis' in VENDOR_LIST; assert 'kis' in VENDOR_METHODS['get_stock_data']"`
- [x] `pytest tests/test_ta_kis_adapter.py -m network` PASS — 005930에 대해 CSV 30+ 라인 (지난 30일 거래일)
- [x] 같은 테스트가 `005930.KS` 입력에도 동작 (정규화)
- [x] 미국 티커(NVDA) get_stock_data 호출 시 yfinance 폴백 (kis 라우팅 안 됨)
- [x] `python -c "from app.integrations.ta_runner import _resolve_llm_config; print(_resolve_llm_config())"` → provider/model 튜플 출력. LLM_PROVIDER=openai 환경에서도 동작
- [x] yfinance fundamentals/news가 005930에 대해 .KS 자동 부착 (monkey-patch 검증)

## 오픈 이슈 (Open Issues)

- KIS는 펀더멘털 직접 제공 안 함 → yfinance .KS 폴백 사용. 정확도 한계 인지
- 한국어 뉴스는 yfinance에 부족 → Phase 후속 task에서 NewsAPI 또는 네이버 RSS 추가 검토
- propagate() 1회는 LLM 토큰 수만~수백만 단위 비용. 자동 회귀 테스트는 비실용적 → Streamlit UI 수동 트리거 + 결과 캐싱 (Phase D)
- KIS daily_candles는 1회 호출당 100건 제한 가능. 1년 이상 일봉은 페이지네이션 필요 (1차는 최근 90거래일 정도만)
- Ollama 사용 시 모델 사전 다운로드 필요 (안내문만 표시)
