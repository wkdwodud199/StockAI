# 구현 노트 — task-006-websocket

> Status: done
> Inputs: kb/tasks/task-006-websocket/design.md
> Outputs: app/kis/websocket.py 완성, app/ui/components.py auto_refresh_toggle, tests/test_websocket_parse.py
> Next step: 라운드트립 도구 (task-007) 또는 추가 기능 사용자 결정

## 설계 대비 변경 사항

| 항목 | 설계 | 실제 | 사유 |
|------|------|------|------|
| 모의 환경 WebSocket 지원 | 미명시 | 명시적으로 거부(KisError raise) | KIS 모의 서버는 WebSocket 미지원 |
| Streamlit 자동 갱신 | WebSocket 직접 연동 | streamlit-autorefresh 폴링 | 모의에서 동작하는 가장 안정적인 경로 |

## 구현 결정

1. **WebSocket은 실전 전용** — `subscribe_ticks(env)`가 `env.is_mock`이면 즉시 KisError. 모의 사용자는 폴링 자동 갱신으로.
2. **streamlit-autorefresh 의존성 추가** — `auto_refresh_toggle()`로 페이지마다 토글 + 주기 선택(3/5/10/30초).
3. **TickMessage 안전 파서** — 비어있는 필드는 0으로 폴백. `_f()` 헬퍼로 `int(float(""))` 예외 차단.
4. **TR_ID 인자화** — 체결가(H0STCNT0)와 호가(H0STASP0) 양쪽 같은 함수로 처리 가능.
5. **단발 구독 + 타임아웃** — `duration_sec` 후 자동 종료. 무한 루프 방지.

## 발생한 이슈

- 초기 파서가 `int(float(""))`에서 ValueError → `_f()` 헬퍼로 안전화.
- 거래량 위치(body[12])가 KIS 응답에서 항상 채워지진 않음 → 누락 시 0.

## 테스트 결과

| 테스트 | 결과 |
|--------|------|
| valid tick payload 파싱 | pass |
| 잘못된 TR_ID 거부 | pass |
| 빈 payload / JSON ack 거부 | pass |
| 잘림(truncated) body 거부 | pass |

전체: 31/31 PASS (12 unit + 8 어댑터 + 7 뉴스 + 4 websocket)

## 산출물

- `app/kis/websocket.py` (130 LOC) — approval_key + parse_tick_payload + subscribe_ticks
- `app/ui/components.py` `auto_refresh_toggle()` 추가 (25 LOC)
- `app/ui/pages/domestic_trade.py` 시세 탭에 토글 노출
- `tests/test_websocket_parse.py` (4 tests)
- `pyproject.toml` `streamlit-autorefresh>=1.0` 추가
- `scripts/smoke_market_hours.ps1` — 장중 라운드트립 도구 (D)
