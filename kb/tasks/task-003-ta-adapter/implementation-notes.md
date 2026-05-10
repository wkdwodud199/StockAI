# 구현 노트 — task-003-ta-adapter

> Status: done
> Inputs: kb/tasks/task-003-ta-adapter/design.md
> Outputs: TA dataflows kis_api.py + kis_config.py, app/integrations/ta_kis_patch.py + ta_runner.py, tests/test_ta_kis_adapter.py
> Next step: task-004-streamlit-ui (Phase D — UI에서 ta_runner.run_analysis_streaming 노출)

## 설계 대비 변경 사항

| 항목 | 설계 내용 | 실제 구현 | 변경 사유 |
|------|-----------|-----------|-----------|
| stockstats date 처리 | sdf.iterrows() + row["date"] | date_series 별도 보존 + sdf[indicator] 시리즈 인덱싱 | stockstats wrap()이 date 컬럼을 인덱스로 흡수해 row["date"] KeyError 발생 |
| ta_runner.run_analysis 자동 검증 | propagate() 1회 실행 검증 | LLM 키 미설정으로 보류 (Streamlit에서 사용자 트리거 시 검증) | ANTHROPIC_API_KEY=""(빈값)이라 LLM 초기화 실패. 비용·키 발급은 사용자 결정 |

## 구현 결정 기록

1. **kis_api.py를 TradingAgents 폴더 안에 두되 `app.kis.*` import** — Codex-With-Claude 워크플로우 "수정은 dataflows/kis_*.py 만"이라는 규칙 준수.
2. **VENDOR_LIST에 'kis' 추가 + VENDOR_METHODS 등록** — TA 기존 fallback 체인이 자동으로 KIS 우선, yfinance 폴백 처리.
3. **yfinance 함수 monkey-patch** — KRX 6자리 티커가 yfinance fundamentals/news 호출에 들어갈 때 `.KS` 자동 부착. interface.py가 직접 import한 참조도 갱신.
4. **idempotent guard** — Streamlit이 페이지 전환마다 호출해도 1회만 적용.
5. **LLM provider 환경변수 우선순위** — `LLM_PROVIDER` → provider, `TA_DEEP_LLM`/`TA_QUICK_LLM` → 모델명 오버라이드.
6. **CSV 캐시** — `TradingAgents/dataflows/data_cache/kis/<ticker>_<start>_<end>.csv` 디스크 hit.
7. **`_normalize_result()`** — propagate() 결과를 텍스트 필드 + signal + raw_state로 정리해 UI 카드 렌더링 용이.

## 발생한 이슈

- **stockstats KeyError 'date'** — wrap()이 date 컬럼 흡수. date_series 별도 보존으로 해결.
- **interface.py import-time 직접 참조** — 모듈 attribute뿐 아니라 interface 모듈의 attribute도 갱신. 두 위치 모두 처리.
- **propagate() 자동 회귀 부재** — LLM 비용/키 부담. CLI `python -c "from app.integrations.ta_runner import run_analysis; print(run_analysis('005930', '2026-05-09'))"`로 사용자 수동.

## 테스트 결과

| 테스트 기준 (design.md 참조) | 결과 | 비고 |
|------------------------------|------|------|
| KIS 벤더 등록 (VENDOR_LIST + VENDOR_METHODS) | pass | test_patch_registers_kis_vendor |
| data_vendors KIS first 라우팅 | pass | test_data_vendors_routed_to_kis_first |
| KRX 6자리 → .KS 자동 부착 | pass | test_yfinance_wrap_adds_ks_for_krx |
| KIS get_stock_data CSV 반환 (005930) | pass | 8 candles |
| 005930.KS 입력도 정상 | pass | test_kis_get_stock_data_handles_yf_suffix |
| KIS get_indicators close_50_sma | pass | "## close_50_sma values..." |
| LLM_PROVIDER=anthropic/openai/ollama | pass | unknown은 ValueError |
| idempotent (2회 호출) | pass | test_patch_idempotent |
| propagate() 005930 KRX 동작 | manual | LLM 키 필요 — Streamlit에서 트리거 |

전체: 20/20 PASS, 1 skipped (market hours)

## 산출물

- `TradingAgents/tradingagents/dataflows/kis_api.py` (167 LOC)
- `TradingAgents/tradingagents/dataflows/kis_config.py` (24 LOC)
- `TradingAgents/tradingagents/dataflows/data_cache/kis/` (gitignored)
- `app/integrations/ta_kis_patch.py` (110 LOC)
- `app/integrations/ta_runner.py` (115 LOC)
- `tests/test_ta_kis_adapter.py` (105 LOC, 8 tests)
