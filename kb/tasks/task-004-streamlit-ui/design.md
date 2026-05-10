# 설계 문서 — task-004-streamlit-ui (Streamlit 7-메뉴 대시보드)

> Status: done
> Inputs: kb/tasks/task-002-kis-client/, kb/tasks/task-003-ta-adapter/, app/kis/* (시세/주문/계좌), app/integrations/ta_runner.py
> Outputs: app/ui/streamlit_app.py + components.py + pages/{home,domestic_trade,overseas_trade,futures_trade,ai_analysis}.py, scripts/run.ps1 동작
> Next step: task-005-polish (README 정리, Phase F 회귀, git 첫 커밋)

## 목표 (Objective)

7개 메뉴(홈/모의국내/모의해외/모의선물옵션/실전국내/실전해외/AI분석)를 갖는 Streamlit 단일 진입점 대시보드를 작성한다. 실전 메뉴는 PIN 게이트로 잠금. AI 분석 메뉴는 TradingAgents 다중 에이전트를 호출.

## 범위 (Scope)

- 포함:
  - `streamlit_app.py` 사이드바 라우터
  - 페이지: 홈, 국내(실/모의 공용), 해외(실/모의 공용), 선물옵션(모의), AI
  - 공통 컴포넌트: 시세 패널, 호가창, 일봉 차트, 잔고/보유, 주문 폼, 실전 PIN 게이트
  - PIN 잠금/해제 + 사이드바에서 잠그기 버튼
- 제외:
  - WebSocket 실시간 자동 갱신 (수동 새로고침)
  - 알고리즘 자동매매
  - 다중 사용자 / 인증

## 제약 (Constraints)

- 파일은 `app/ui/`에만 배치
- 모든 KIS 호출은 기존 `app/kis/*` 모듈 경유 (UI에서 직접 requests 호출 금지)
- 실전 매매 폼은 PIN 잠금 해제 + form-level 확인 체크박스 둘 다 필요
- 한 번 잠금 해제된 실전 모드는 사이드바 "잠그기" 버튼으로 즉시 잠글 수 있음
- 화폐 단위 분리: 국내 ₩, 해외 $

## 구현 단계 (Implementation Steps)

1. `app/ui/components.py` — 시세, 호가, 차트, 잔고, 주문 폼, PIN 게이트 공통화
2. `app/ui/pages/home.py` — 인사 + 모의 국내 계좌 요약
3. `app/ui/pages/domestic_trade.py` — env 인자로 실/모의 공용 (3 탭: 시세·주문 / 차트 / 잔고)
4. `app/ui/pages/overseas_trade.py` — 거래소 선택 + 시세·주문 + 잔고 (USD)
5. `app/ui/pages/futures_trade.py` — 모의 전용 (단일 페이지 시세+주문)
6. `app/ui/pages/ai_analysis.py` — LLM 키 검사 + 종목·날짜 입력 + run_analysis_streaming 호출 + 결과 카드
7. `app/ui/streamlit_app.py` — 사이드바 메뉴 + 라우팅

## 파일/모듈 영향 (Affected Files/Modules)

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `app/ui/streamlit_app.py` | create | 진입점, 사이드바 메뉴, 라우팅 |
| `app/ui/components.py` | create | 6개 공통 컴포넌트 |
| `app/ui/pages/__init__.py` | create | 빈 패키지 마커 |
| `app/ui/pages/home.py` | create | 홈 페이지 |
| `app/ui/pages/domestic_trade.py` | create | 국내주식 (실/모의 공용) |
| `app/ui/pages/overseas_trade.py` | create | 해외주식 (실/모의 공용) |
| `app/ui/pages/futures_trade.py` | create | 선물옵션 모의 전용 |
| `app/ui/pages/ai_analysis.py` | create | TradingAgents 트리거 + 결과 표시 |

## 테스트 기준 (Test Criteria)

- [x] 모든 ui 모듈 syntax 통과 (`ast.parse`)
- [x] 모든 ui 모듈 import 성공
- [x] `streamlit run app/ui/streamlit_app.py --server.headless true` → HTTP 200 + `/_stcore/health` = "ok"
- [x] 트레이스백 없는 깨끗한 부팅
- [x] 사이드바에서 7개 메뉴 모두 선택 가능 (수동 검증 — 사용자 브라우저)

## 오픈 이슈 (Open Issues)

- 실거래 PIN은 `.env REAL_MODE_PIN`에 평문 저장 — OS keyring 통합은 후속 작업
- 화면 자동 새로고침 미구현 (Streamlit 기본 동작)
- 호가/체결 실시간은 미구현 — task-005 또는 별도 task로 WebSocket 연동
- 한국어 폰트는 시스템 의존 (한글 차트 라벨이 깨질 수 있음)
