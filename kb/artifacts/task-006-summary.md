# 산출물 요약 — task-006-websocket

> Status: done
> Inputs: kb/tasks/task-006-websocket/implementation-notes.md
> Outputs: 본 요약
> Next step: 사용자 결정 — 추가 기능 또는 운영 단계

## 작업 요약

- **Task ID**: task-006-websocket
- **제목**: KIS WebSocket 실시간 시세 + Streamlit 자동 갱신
- **완료일**: 2026-05-10

## 산출물

| 산출물 | 경로 | 설명 |
|--------|------|------|
| WebSocket 모듈 완성 | `app/kis/websocket.py` | approval_key, parse_tick_payload (안전 파싱), subscribe_ticks (단발 구독 + 타임아웃) |
| 자동 갱신 토글 | `app/ui/components.py::auto_refresh_toggle` | 페이지마다 3/5/10/30초 토글 |
| 거래 페이지 통합 | `app/ui/pages/domestic_trade.py` | 시세 탭에 자동 갱신 |
| 의존성 | `pyproject.toml` | streamlit-autorefresh>=1.0 |
| 라운드트립 도구 | `scripts/smoke_market_hours.ps1` | 장중에만 실행, 005930 1주 매수→매도→잔고 |
| 테스트 | `tests/test_websocket_parse.py` | 4 tests pass |

## 주요 결정

- **모의 환경 WebSocket 사용 거부** — KIS 정책. 모의는 폴링 자동 갱신.
- **streamlit-autorefresh 도입** — 의존성 1개 추가로 모든 페이지 hot-refresh.
- **WebSocket 메시지 안전 파서** — body 누락 필드는 0으로 폴백.

## 검증

```
$ python -m pytest tests
31 passed in 5.54s

$ # 사용자 직접: 장중에 라운드트립
$ .\scripts\smoke_market_hours.ps1
```

## 관련 문서

- 설계: `kb/tasks/task-006-websocket/design.md`
- 구현 노트: `kb/tasks/task-006-websocket/implementation-notes.md`
