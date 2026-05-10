# 산출물 요약 — task-002-kis-client

> Status: done
> Inputs: kb/tasks/task-002-kis-client/implementation-notes.md
> Outputs: 본 요약 + Phase C 진입 신호
> Next step: task-003-ta-adapter (TradingAgents KIS 데이터플로우 어댑터)

## 작업 요약

- **Task ID**: task-002-kis-client
- **제목**: KIS Open API 클라이언트 라이브러리
- **완료일**: 2026-05-10

## 산출물 목록

| 산출물 | 경로 | 설명 |
|--------|------|------|
| KIS 클라이언트 패키지 | `app/kis/` | 18개 모듈, 환경 3종(real_*, mock_*, mock_futures) 라우팅 |
| 시세/주문/계좌 CLI | `python -m app.kis.{auth,quote_domestic,account,order_domestic,...}` | typer 기반, .env 자동 로드 |
| 자격증명 마이그레이터 | `scripts/migrate_secrets.ps1` | MTS_API.txt → .env 1회 변환 |
| 단위 테스트 | `tests/test_kis_*.py` | 12건 PASS (network 불필요) |
| 통합 스모크 | `tests/smoke_kis_mock.py` | 5건 PASS, 매매 라운드트립은 장중 시간만 |
| 토큰 캐시 | `.kis_cache/token_<env>.json` | gitignored |

## 주요 결정

- **자체 구현 채택** (python-kis dependency 거부) — 실/모의 동시 보유, 선물옵션 모의 분리 라우팅 필요.
- **토큰 버킷 capacity=1 강제** — KIS sliding-window 카운터 회피. burst 금지.
- **EGW00201 + HTTP 500 자동 retry** (1.2s 백오프) — 서버 카운터가 클라이언트보다 엄격할 때 회복.
- **선물옵션은 MOCK_FUTURES로만 라우팅** — 실전 사고 차단.
- **TradingAgents 포크 금지** — 외부 라이브러리는 그대로 두고, Phase C에서 dataflows에 kis_api.py만 추가.

## 검증 evidence

```
2026-05-10 21:22:17 [WARNING] kis.http: [mock_domestic] HTTP 500 + EGW00201 — backoff and retry
--- 1. current_price ---
price=268,500.0  prev_close=271,500.0
--- 2. daily_candles ---
8 candles, last_close=268,500.0
--- 3. orderbook ---
bids=10 asks=10
--- 4. balance ---
deposit=500,000,000 eval=500,000,000
ALL 4 calls succeeded with auto-retry on EGW00201
```

## 관련 문서

- 설계: `kb/tasks/task-002-kis-client/design.md`
- 구현 노트: `kb/tasks/task-002-kis-client/implementation-notes.md`
- 마스터 플랜: `C:\Users\wkdwo\.claude\plans\typed-honking-kurzweil.md`
