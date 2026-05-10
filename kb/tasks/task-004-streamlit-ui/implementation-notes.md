# 구현 노트 — task-004-streamlit-ui

> Status: done
> Inputs: kb/tasks/task-004-streamlit-ui/design.md
> Outputs: app/ui/* 8개 파일, Streamlit 부팅 검증
> Next step: task-005-polish — README 정리, 첫 커밋, Phase F 회귀

## 설계 대비 변경 사항

| 항목 | 설계 내용 | 실제 구현 | 변경 사유 |
|------|-----------|-----------|-----------|
| 페이지 모듈 분리 | 페이지마다 별도 모듈 | domestic/overseas는 env 인자로 1개 모듈 공용 (실/모의) | 코드 중복 절감 — 실/모의는 라우팅·자격증명만 다름 |
| 호가 자동 갱신 | 미명시 | 수동 새로고침 (Streamlit 기본 모델) | WebSocket 실시간은 task 추가 필요 |

## 구현 결정 기록

1. **pages/domestic_trade.py에 env 파라미터** — `render(env: KisEnvironment)`. streamlit_app.py가 메뉴 선택에 따라 MOCK_DOMESTIC 또는 REAL_DOMESTIC을 전달.
2. **실전 모드 PIN 게이트** — `render_real_mode_gate()` 함수가 잠금 해제 폼을 그리고 True/False 반환. 페이지 본문은 True일 때만 렌더.
3. **사이드바 "잠그기" 버튼** — 한 번 해제된 실전 모드를 즉시 다시 잠글 수 있도록.
4. **AI 분석 LLM 키 사전 점검** — 키 미설정 시 페이지 상단 빨간 경고. 분석 시작 버튼은 그대로 활성화 (사용자가 환경변수 갱신 후 즉시 테스트 가능).
5. **`session_state["ai_picked_ticker"]`** — AI 분석 결과 카드의 "거래 페이지로 보내기" 버튼이 종목코드를 세션에 저장 → 국내 거래 페이지의 종목 입력란 default로 사용.

## 발생한 이슈

- 없음 (syntax/import 모두 1회 통과)

## 테스트 결과

| 테스트 기준 (design.md 참조) | 결과 | 비고 |
|------------------------------|------|------|
| ui 모듈 syntax 통과 | pass | 9 files OK |
| ui 모듈 import 성공 | pass | components + 5 pages |
| Streamlit HTTP 200 | pass | 127.0.0.1:8501 |
| /_stcore/health = ok | pass | |
| 트레이스백 없는 부팅 | pass | Uvicorn 정상 시작 |

## 산출물

- `app/ui/streamlit_app.py` — 메인 진입 + 라우터 (75 LOC)
- `app/ui/components.py` — 공통 컴포넌트 (170 LOC)
- `app/ui/pages/home.py` (35 LOC)
- `app/ui/pages/domestic_trade.py` (75 LOC)
- `app/ui/pages/overseas_trade.py` (60 LOC)
- `app/ui/pages/futures_trade.py` (47 LOC)
- `app/ui/pages/ai_analysis.py` (75 LOC)
