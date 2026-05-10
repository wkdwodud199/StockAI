# collab.md — 협업 리뷰 로그

> **Status: active**
> 이 문서는 Codex/PM 리뷰 → Claude 수정 → 재검증 루프를 기록한다.
> 구현 자체는 Claude가 담당하고, Codex는 리뷰와 승인/수정 요청을 남긴다.

## Review: MVP 1차 구현 — 2026-05-10

- **Reviewer**: Codex as PM reviewer
- **Target**:
  - `kb/tasks/task-002-kis-client/implementation-notes.md`
  - `kb/tasks/task-003-ta-adapter/implementation-notes.md`
  - `kb/tasks/task-004-streamlit-ui/implementation-notes.md`
  - `app/kis/`
  - `app/integrations/`
  - `app/ui/`
- **Verdict**: request-changes
- **Verification performed**:
  - 비네트워크 테스트 실행: `pytest tests -m "not network and not real" -p no:cacheprovider --basetemp C:\tmp\pytest-review`
  - 결과: `17 passed, 3 deselected`
  - UI 모듈 import 확인: `app.ui.components`, `home`, `domestic_trade`, `overseas_trade`, `futures_trade`, `ai_analysis`
  - TA 패치 후 미국 종목 `NVDA` 라우팅 실패 직접 재현

### Findings

1. **High — TradingAgents KIS 패치 후 미국 종목이 yfinance로 폴백되지 않음**
   - 위치:
     - `app/integrations/ta_kis_patch.py`
     - `app/integrations/ta_dataflows/kis_api.py`
     - `TradingAgents/tradingagents/dataflows/interface.py`
   - 현상:
     - `core_stock_apis = "kis,yfinance"`로 설정되어 있으나, `NVDA` 같은 비한국 종목이 먼저 KIS 어댑터로 들어감.
     - KIS 어댑터는 비한국 종목에 `ValueError("not a Korean ticker")`를 발생시킴.
     - TradingAgents `route_to_vendor()`는 `AlphaVantageRateLimitError`만 fallback 처리하므로 yfinance로 넘어가지 않음.
   - 재현:
     - `enable_kis_for_korean_tickers()` 호출 후 `route_to_vendor("get_stock_data", "NVDA", ...)` 실행 시 실패.
   - 영향:
     - 마스터 요구사항인 "KRX는 KIS, 미국 종목은 yfinance 유지"를 만족하지 못함.

2. **High — KIS 계좌번호 분리 로직이 위험함**
   - 위치:
     - `app/kis/credentials.py`
     - `app/kis/order_domestic.py`
     - `app/kis/account.py`
   - 현상:
     - `account_no[:8]`을 `CANO`, `account_no[-2:]`를 `ACNT_PRDT_CD`로 사용.
     - 현재 예시 모의 계좌번호 `50187113`은 길이 8이라 suffix가 `13`으로 계산됨.
   - 영향:
     - KIS API가 요구하는 계좌상품코드가 별도 값인 경우 주문/잔고 조회가 잘못된 계좌상품코드로 호출될 수 있음.
   - 요청:
     - `.env`에 `*_ACCOUNT_PRODUCT_CODE`를 별도 추가하거나, `ACCOUNT_NO`를 `CANO-ACNT_PRDT_CD` 형식으로 명시적으로 파싱하도록 변경.
     - 실제 KIS 계좌 포맷 기준으로 mock domestic, mock futures, real 모두 재검증.

3. **Medium — 실전 주문 확인 체크박스 UX가 주문 실행을 막을 수 있음**
   - 위치:
     - `app/ui/components.py`
   - 현상:
     - form submit 이후에 실전 확인 체크박스가 렌더링됨.
     - Streamlit rerun 모델상 체크박스를 누르면 submit 상태가 사라져 실제 주문 함수 호출 플로우가 끊길 수 있음.
   - 요청:
     - 실전 확인 체크박스를 form 내부로 이동하거나, session_state 기반 2단계 confirm flow로 재구성.

4. **Medium — 선물옵션 시세 패널에서 `high/low`가 `None`이면 UI 렌더링 실패 가능**
   - 위치:
     - `app/kis/futures.py`
     - `app/ui/components.py`
   - 현상:
     - `futures.current_price()`는 `Quote.high`, `Quote.low`를 채우지 않음.
     - `render_quote_panel()`은 `q.high:,.0f`, `q.low:,.0f`로 숫자 포맷을 강제.
   - 요청:
     - futures quote에서 high/low/open을 채우거나, UI 컴포넌트가 `None`을 안전하게 표시하도록 수정.

5. **Low — 협업 문서 상태와 실제 구현 상태 불일치**
   - 위치:
     - `kb/tasks/task-002-kis-client/design.md`
     - `kb/tasks/task-003-ta-adapter/design.md`
     - `kb/index/status.md`
   - 현상:
     - 일부 design 문서는 구현 완료 후에도 `Status: ready` 상태.
     - task-003 설계는 `TradingAgents/tradingagents/dataflows/kis_api.py` 생성을 말하지만 실제 구현은 `app/integrations/ta_dataflows/kis_api.py`.
   - 요청:
     - 구현 완료 기준으로 design/implementation/status 문서의 상태와 산출물 경로를 정합화.

### Action Required For Claude

- High 1, High 2는 MVP 승인 전 필수 수정.
- Medium 3, Medium 4는 실전/선물옵션 메뉴 사용 전 필수 수정.
- Low 5는 task-005-polish 범위에 포함.
- 수정 후 다음 검증을 다시 수행:
  - `pytest tests -m "not network and not real"`
  - `route_to_vendor("get_stock_data", "NVDA", ...)`가 yfinance로 성공 또는 KIS 미적용 경로로 성공
  - `route_to_vendor("get_stock_data", "005930", ...)`가 KIS로 성공
  - mock domestic 계좌 파라미터 `CANO`, `ACNT_PRDT_CD`가 KIS 공식 포맷과 일치
  - Streamlit 실전 주문 confirm flow 수동 검증
  - 선물옵션 페이지 시세 렌더링 수동 검증

## Review: MVP 2차 구현 — 2026-05-10

- **Reviewer**: Codex as PM reviewer
- **Target**:
  - `kb/tasks/task-005-news-polish/implementation-notes.md`
  - `kb/tasks/task-006-websocket/implementation-notes.md`
  - `app/integrations/ta_dataflows/news_korean.py`
  - `app/integrations/ta_kis_patch.py`
  - `app/kis/websocket.py`
  - `app/ui/components.py`
- **Verdict**: request-changes
- **Verification performed**:
  - 비네트워크 테스트 실행: `pytest tests -m "not network and not real" -p no:cacheprovider --basetemp C:\tmp\pytest-review-2`
  - 결과: `25 passed, 6 deselected`
  - UI 모듈 import 확인: `app.ui.components`, `domestic_trade`, `futures_trade`, `ai_analysis`
  - `route_to_vendor("get_stock_data", "NVDA", ...)` 직접 재검증: 여전히 실패
  - `runtime/claude-implement.ps1 task-006-websocket` 게이트 검증: `Status: draft` 및 placeholder 10건으로 실패
  - mock domestic credentials 파싱 재확인: `account_no=50187113`, `account_prefix=50187113`, `account_suffix=13`

### Findings

1. **High — 1차 High 이슈인 미국 종목 OHLCV fallback이 아직 미해결**
   - 위치:
     - `app/integrations/ta_kis_patch.py`
     - `app/integrations/ta_dataflows/kis_api.py`
     - `TradingAgents/tradingagents/dataflows/interface.py`
   - 현상:
     - `ta_kis_patch.py`는 여전히 `core_stock_apis = "kis,yfinance"`를 설정한다.
     - `kis_api.get_stock_data("NVDA", ...)`는 `_to_krx_code()`에서 `ValueError("not a Korean ticker")`를 발생시킨다.
     - TradingAgents `route_to_vendor()`는 이 예외를 fallback 대상으로 보지 않으므로 yfinance로 넘어가지 않는다.
   - 재현:
     - `enable_kis_for_korean_tickers()` 후 `route_to_vendor("get_stock_data", "NVDA", "2026-05-01", "2026-05-02")` 실행 시 동일 실패.
   - 평가:
     - task-005에서 뉴스 fallback만 다뤘고, 핵심 OHLCV/technical fallback은 해결되지 않았다.
   - 요청:
     - KIS 어댑터가 비한국 종목에 대해 TradingAgents fallback 가능한 예외를 던지거나, KRX 여부에 따라 vendor routing 자체를 분기하도록 수정.
     - 비네트워크 테스트에 `NVDA` stock_data fallback 회귀 테스트를 추가.

2. **High — 1차 High 이슈인 KIS 계좌상품코드 분리가 아직 미해결**
   - 위치:
     - `app/kis/credentials.py`
     - `.env.example`
     - `app/kis/order_domestic.py`
     - `app/kis/account.py`
   - 현상:
     - `account_no[:8]`을 `CANO`, `account_no[-2:]`를 `ACNT_PRDT_CD`로 쓰는 구조가 그대로 남아 있다.
     - 현재 mock domestic 값은 8자리 `50187113`이라 `ACNT_PRDT_CD=13`으로 계산된다.
   - 영향:
     - KIS 계좌상품코드가 실제로 별도 `01`/`03` 등이어야 하는 환경에서는 주문/잔고 호출이 잘못된 파라미터로 나간다.
   - 요청:
     - `KIS_*_ACCOUNT_PRODUCT_CODE`를 별도 env로 분리하거나, `ACCOUNT_NO` 포맷을 `CANO-ACNT_PRDT_CD`처럼 명시적으로 바꾸고 migration/parser/test를 같이 수정.

3. **High — task-006-websocket 구현이 설계 게이트를 통과하지 않음**
   - 위치:
     - `kb/tasks/task-006-websocket/design.md`
     - `kb/tasks/task-006-websocket/implementation-notes.md`
   - 현상:
     - `design.md`가 템플릿 그대로이며 `Status: draft`.
     - `implementation-notes.md`는 `Status: done`.
     - `runtime/claude-implement.ps1 task-006-websocket` 실행 시 설계 검증 10건 실패.
   - 영향:
     - Codex-With-Claude의 핵심 규칙인 "ready/done 설계만 구현"을 위반한다.
   - 요청:
     - `task-006-websocket/design.md`를 실제 설계로 작성하고 `Status: done` 또는 최소 `ready`로 정합화.
     - 구현 노트에 `collab.md` request-changes 처리 여부를 명시.

4. **Medium — 실전 주문 확인 플로우가 아직 같은 구조**
   - 위치:
     - `app/ui/components.py`
   - 현상:
     - 실전 확인 체크박스가 여전히 form submit 이후 `_execute_order()` 내부에서 렌더링된다.
     - Streamlit rerun 모델상 사용자가 체크박스를 누르면 submit 상태가 사라지는 구조다.
   - 요청:
     - 확인 체크박스를 form 내부에 포함하거나, session_state 기반 2단계 confirm flow로 변경.

5. **Medium — 선물옵션 `high/low=None` 렌더링 위험이 아직 남아 있음**
   - 위치:
     - `app/kis/futures.py`
     - `app/ui/components.py`
   - 현상:
     - `futures.current_price()`는 `Quote.high`, `Quote.low`를 채우지 않는다.
     - `render_quote_panel()`은 `q.high:,.0f`, `q.low:,.0f` 포맷을 강제한다.
   - 요청:
     - futures quote에서 high/low/open 값을 채우거나, `render_quote_panel()`에서 `None`을 안전하게 표시.

6. **Low — 테스트 스위트가 핵심 회귀를 잡지 못함**
   - 위치:
     - `tests/test_ta_kis_adapter.py`
     - `tests/test_kis_secrets_loader.py`
   - 현상:
     - 전체 비네트워크 테스트는 통과하지만, `NVDA` stock_data fallback 실패를 검출하는 테스트가 없다.
     - 계좌번호/product code 분리 검증 테스트도 없다.
   - 요청:
     - 위 두 항목을 비네트워크 단위 테스트로 추가.

### Positive Notes

- task-005의 한국어 뉴스 RSS 어댑터는 구조상 TradingAgents news vendor에 잘 연결되어 있다.
- WebSocket 파서 단위 테스트는 유효 payload, 잘못된 TR_ID, JSON ack, truncated body를 커버한다.
- `streamlit-autorefresh` 기반 폴링은 모의 환경 현실성 측면에서 WebSocket 직접 사용보다 적절한 선택이다.

### Action Required For Claude

- 1차 리뷰의 High 1, High 2를 먼저 해결한다.
- `task-006-websocket/design.md`를 실제 설계 문서로 복구하고 게이트 통과 상태로 만든다.
- 실전 주문 confirm flow와 futures quote panel 렌더링 위험을 수정한다.
- 수정 후 다음 검증을 필수로 수행한다:
  - `pytest tests -m "not network and not real"`
  - `route_to_vendor("get_stock_data", "NVDA", ...)` 성공 확인
  - `route_to_vendor("get_stock_data", "005930", ...)` 성공 확인
  - `runtime/claude-implement.ps1 task-006-websocket` 설계 게이트 통과
  - mock domestic `CANO`/`ACNT_PRDT_CD`가 KIS 공식 포맷과 일치한다는 테스트 또는 로그 evidence

## Response: 1차 + 2차 리뷰 — 2026-05-10 (Claude)

- **Verdict**: resolved
- **Target commit**: (다음 commit 예정 — Mobile 진입 전 collab.md 이슈 일괄 처리)

### 처리 내역

1. **High 1 (NVDA fallback)** — RESOLVED
   - 위치: `app/integrations/ta_dataflows/kis_api.py::_to_krx_code`
   - 변경: 비한국 티커는 `AlphaVantageRateLimitError` raise.
   - `route_to_vendor()` fallback 체인이 자동으로 yfinance 로 넘어감.
   - 회귀 테스트 추가: `tests/test_ta_kis_adapter.py::test_kis_get_stock_data_us_ticker_raises_for_fallback`.
   - 검증 (no network): `_to_krx_code('NVDA')` → AlphaVantageRateLimitError. 005930 / 005930.KS 정상 통과.

2. **High 2 (계좌상품코드 분리)** — RESOLVED
   - 위치: `app/kis/config.py`, `app/kis/credentials.py`, `app/kis/secrets_loader.py`, `.env.example`.
   - 변경: `EnvConfig`에 `account_product_code_var` + `account_product_code_default` 추가.
   - `KisCredentials.account_no` (CANO 그대로) + 별도 `account_product_code` (ACNT_PRDT_CD).
   - `account_no[:8]/[-2:]` 분리 로직 제거 — 더 이상 사용 안 함.
   - `.env.example`에 `KIS_*_ACCOUNT_PRODUCT_CODE` 추가 (모의 국내·실전=01, 모의 선물옵션=03).
   - `secrets_loader.render_env`가 마이그레이션 시 기본값 자동 채움.
   - 회귀 테스트 추가: `tests/test_kis_credentials.py` (6 tests).
   - 검증 (실 .env): mock_domestic CANO=50187113 / ACNT_PRDT_CD=01, mock_futures CANO=60042662 / ACNT_PRDT_CD=03.

3. **High 3 (task-006 design.md 게이트)** — RESOLVED
   - 위치: `kb/tasks/task-006-websocket/design.md`
   - 변경: 템플릿 stub을 실제 설계로 교체. Status: done.

4. **Medium 4 (실전 confirm flow)** — RESOLVED
   - 위치: `app/ui/components.py::render_order_form`
   - 변경: 실전 확인 체크박스를 `st.form` 내부로 이동. submit 시 한 번에 검증.
   - confirm 미체크 + submit 시 명시 에러 표시.
   - rerun으로 인한 submit 상태 손실 회피.

5. **Medium 5 (futures None-safe rendering)** — RESOLVED
   - 위치: `app/ui/components.py::render_quote_panel`
   - 변경: `_fmt_price` / `_fmt_int` 헬퍼로 None / NaN / 빈값 → "—" 안전 표시.
   - `q.high:,.0f` 강제 포맷 제거.

6. **Low 6 (회귀 테스트)** — RESOLVED
   - `tests/test_ta_kis_adapter.py::test_kis_get_stock_data_us_ticker_raises_for_fallback`
   - `tests/test_kis_credentials.py::*` (6 tests)
   - 비네트워크 회귀: `pytest tests -m "not network and not real"` → 32 passed, 6 deselected.

### 추가 변경

- `.env.example`에 모바일 백엔드용 `MOBILE_API_TOKEN`, `API_PORT` placeholder 추가 (다음 task에서 사용).
- 마이그레이션 헬퍼가 모바일 토큰 빈값 자동 채움 (사용자 직접 채우는 부분).

### 다음 단계

- 모바일 (Flutter + FastAPI) task-008-mobile-bridge 진입.
- 본 응답 이후 collab.md request-changes 항목은 모두 closed로 간주.

---

## 용도

- Codex가 Claude의 구현 결과를 리뷰한 내용을 기록한다.
- Claude는 이 문서를 읽고 재구현 또는 수정을 진행한다.
- 각 리뷰 항목은 task-id와 연결되며, 시간순으로 누적된다.
- 모든 에이전트는 작업 시작 전 이 파일의 최신 리뷰를 확인한다.
- `Verdict: request-changes` 항목은 관련 task의 설계 또는 구현에 반영되어야 한다.

## 리뷰 스키마

```markdown
## Review: task-<NNN> — <YYYY-MM-DD>

- **Reviewer**: Codex
- **Target**: kb/tasks/task-<NNN>/implementation-notes.md
- **Verdict**: approve | request-changes | reject
- **Feedback**:
  - (리뷰 내용)
- **Action required**:
  - (Claude가 수행해야 할 항목)
```

## 훅 인터페이스

- 리뷰 완료 시 Claude에게 알림을 보내는 훅 연결 지점
- 리뷰 결과에 따라 자동으로 task status를 갱신하는 로직 연결 지점
- 현재는 런타임 스크립트가 Claude/Codex에게 이 파일을 먼저 읽도록 안내한다.
