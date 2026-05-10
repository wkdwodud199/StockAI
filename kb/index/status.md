# 작업 현황 (Status Board)

> 마지막 갱신: 2026-05-10

## 활성 작업

| Task ID | 제목 | Status | 담당 | 비고 |
|---------|------|--------|------|------|
| task-005-polish | 스크립트·패키징·문서화 마감 | ready | (대기) | Phase E/F — 첫 git 커밋 + 회귀 |

## 예약 (큐)

(없음 — MVP는 task-005까지)

## 완료 작업

| Task ID | 제목 | 완료일 | 산출물 |
|---------|------|--------|--------|
| task-001 | 워크스페이스 v1 초기 scaffold (Codex-With-Claude 템플릿) | 2026-04-17 | [summary](../artifacts/task-001-summary.md) |
| (Phase A) | Stock_MTS_TA 부트스트랩: kb/, runtime/, templates/, .gitignore, .env.example, pyproject.toml, venv, app/ 스켈레톤 | 2026-05-10 | (이 status.md 갱신) |
| task-002-kis-client | KIS Open API 클라이언트 라이브러리 (auth, quote, order, account, futures, websocket; 17 테스트 PASS) | 2026-05-10 | [summary](../artifacts/task-002-summary.md) |
| task-003-ta-adapter | TradingAgents KIS 데이터플로우 어댑터 (포크 금지, import-time 패치, 8 테스트 PASS) | 2026-05-10 | [summary](../artifacts/task-003-summary.md) |
| task-004-streamlit-ui | Streamlit 7-메뉴 대시보드 (HTTP 200, 0 트레이스백) | 2026-05-10 | [summary](../artifacts/task-004-summary.md) |

## 마스터 플랜

`C:\Users\wkdwo\.claude\plans\typed-honking-kurzweil.md`

## 다음 단계

```powershell
# Codex에게 설계 위임 (이미 design.md를 수동 작성했으므로 생략 가능)
./runtime/codex-design.ps1 task-002-kis-client "KIS Open API 클라이언트 라이브러리"

# Claude 구현 게이트 검증 + 구현 시작
./runtime/claude-implement.ps1 task-002-kis-client
```
