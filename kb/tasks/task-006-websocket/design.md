# 설계 문서 — task-006-websocket (실시간 시세 + Streamlit 자동 갱신)

> Status: done
> Inputs: kb/tasks/task-002-kis-client/, app/kis/websocket.py 골격, collab.md 1차 리뷰
> Outputs: WebSocket 파서·구독 함수, Streamlit 자동 갱신 토글, 단위 테스트, 라운드트립 도구
> Next step: task-008-mobile-bridge (Flutter+FastAPI)

## 목표 (Objective)

KIS 시세를 실시간으로 표시. KIS 모의 환경은 WebSocket 미지원이므로 모의는 폴링+streamlit-autorefresh로, 실전은 WebSocket(실거래 키 필요)로 처리한다.

## 범위 (Scope)

- 포함:
  - WebSocket approval_key 발급
  - `parse_tick_payload(payload, tr_id)` — 안전 파싱 (누락 필드는 0으로 폴백)
  - `subscribe_ticks(ticker, env, on_tick, duration_sec)` — 단발 구독 + 타임아웃
  - Streamlit `auto_refresh_toggle(key, default_interval)` — 3/5/10/30초 토글
  - 라운드트립 도구 `scripts/smoke_market_hours.ps1`
- 제외:
  - 다종목 동시 구독 / 재접속 자동화
  - 호가창(H0STASP0) 별도 파서 (현재 코드는 TR_ID 파라미터화만)

## 제약 (Constraints)

- 모의 환경 WebSocket 사용 시 명시적 거부 (KisError)
- duration_sec 타임아웃 강제 — 무한 구독 차단
- 메시지 누락 필드는 0으로 폴백 (예외 안 던짐)

## 구현 단계 (Implementation Steps)

1. websocket.py 파서 함수 + 단발 구독 함수
2. Streamlit auto_refresh_toggle 컴포넌트
3. 거래 페이지에 토글 통합
4. pyproject.toml에 streamlit-autorefresh 의존성
5. 단위 테스트 4건
6. 장중 라운드트립 도구 (사용자 트리거)

## 파일/모듈 영향 (Affected Files/Modules)

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `app/kis/websocket.py` | modify | parse_tick_payload + subscribe_ticks 완성 |
| `app/ui/components.py` | modify | auto_refresh_toggle 추가 |
| `app/ui/pages/domestic_trade.py` | modify | 토글 사용 |
| `pyproject.toml` | modify | streamlit-autorefresh 의존성 |
| `tests/test_websocket_parse.py` | create | 4 tests |
| `scripts/smoke_market_hours.ps1` | create | 장중 라운드트립 |

## 테스트 기준 (Test Criteria)

- [x] 유효 tick payload 파싱 (005930, price=268500, change=-3000)
- [x] 잘못된 TR_ID 거부
- [x] 빈 payload, JSON ack 거부
- [x] 잘린 body 거부
- [x] Streamlit auto-refresh 동작 (사용자 브라우저 검증)

## 오픈 이슈 (Open Issues)

- 모의 환경 WebSocket 부재 — KIS 정책 변경 시 재검토
- 호가창(H0STASP0) 파서는 현재 미구현
- 자동 재접속 (네트워크 장애) — 후속 task
