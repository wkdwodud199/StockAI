# 구현 노트 — task-002-kis-client

> Status: done
> Inputs: kb/tasks/task-002-kis-client/design.md
> Outputs: app/kis/* 18개 모듈, app/utils/{ticker,logging}.py, scripts/migrate_secrets.ps1, tests/test_kis_*.py, tests/smoke_kis_mock.py
> Next step: task-003-ta-adapter (TradingAgents KIS dataflow 어댑터)

## 설계 대비 변경 사항

| 항목 | 설계 내용 | 실제 구현 | 변경 사유 |
|------|-----------|-----------|-----------|
| 토큰 만료 leeway | 고정 10일 (REFRESH_BEFORE_SECONDS) | 토큰 수명의 5% 동적 (최소 60s) | 모의 토큰은 24h 만료라 10일 leeway면 항상 만료 판정 → 매번 재발급. 동적 leeway로 실전 90d/모의 24h 양쪽에서 cache HIT 가능 |
| 토큰 버킷 capacity | rate_per_sec와 동일 (burst 허용) | capacity=1 강제 (strict 페이싱) | KIS 서버는 sliding-window 카운터라 burst가 EGW00201 트리거 |
| EGW00201 처리 | KisRateLimitError 즉시 발생 | 1.2초 백오프 후 자동 1회 재시도, 그래도 실패 시 예외 | 서버 카운터가 가끔 우리 토큰 버킷보다 엄격함 → 자동 회복 |
| HTTP 500 처리 | KisHttpError | msg_cd=EGW00201이면 retry, 그 외는 KisError | KIS는 rate limit를 종종 HTTP 500으로 반환 |
| `utils_paths.py` 추가 | 설계에 없음 | 신설 | auth.py ↔ credentials.py 간 PROJECT_ROOT 공유, import 사이클 회피 |

## 구현 결정 기록

1. **자체 KIS 클라이언트 구현** (python-kis dependency 미사용) — 설계대로. 실/모의/선물옵션 환경 라우팅을 한 enum에 묶어야 했고, rate limiter도 환경별 정밀 제어 필요.
2. **TR_ID는 `tr_id_table.py`의 단일 dict에서 라우팅** — 매 호출마다 `get_tr_id(operation, env)` 호출. 환경별 prefix 차이 (T/V) 자동 흡수.
3. **선물옵션 가드** — `_ensure_mock(env)` 함수로 실전 선물옵션 키 사용 시도 차단. `tr_id_table`도 `futures-*` 키를 MOCK_FUTURES에만 등록.
4. **모의 해외주식 자격증명** — KIS 정책상 모의 국내주식 키와 동일 사용 → `MOCK_OVERSEAS`의 secret_env_keys를 `MOCK_DOMESTIC`과 동일하게 설정.
5. **typer 단일 명령 자동 축약** — typer 0.25는 단일 `@app.command()` 앱을 서브커맨드 없이 호출하도록 축약. `auth.py`/`account.py`/`secrets_loader.py`는 서브커맨드명 없이 직접 인자 전달.
6. **CLI 인코딩 mojibake** — Windows 콘솔 cp949에서 한글 출력은 깨져 보이지만 stdin/stdout/file IO는 모두 UTF-8 정상. Streamlit UI에서는 정상 표시될 것.

## 발생한 이슈

- **장외 시간 매수/매도 거부** (msg_cd=40100000): 예상된 동작. 매매 plumbing은 정상 (auth/hashkey/TR_ID 모두 통과 후 서버 비즈니스 룰로 거부). 라운드트립 테스트는 `@market_hours` 마커로 자동 skip 처리.
- **EGW00201 rate limit**: 토큰 버킷이 정확히 250ms 페이싱하는데도 발생. KIS 서버 카운터가 우리 클라이언트보다 엄격한 sliding window. 자동 retry 로직 추가로 회복.
- **TradingAgents requirements.txt = '.'**: 자기 자신 참조라 단독 사용 불가. `pip install -e ./TradingAgents`는 pyproject.toml 사용해서 정상 설치됨.

## 테스트 결과

| 테스트 기준 (design.md 참조) | 결과 | 비고 |
|------------------------------|------|------|
| migrate_secrets.ps1 → .env 5쌍 채워짐 | pass | 9개 KIS 키 + 5개 LLM/UI 키 = 14줄 |
| auth --env mock_domestic 토큰 발급 + 캐시 | pass | `.kis_cache/token_mock_domestic.json` 생성, 346자 JWT |
| 캐시 HIT (재실행 시 네트워크 0회) | pass | 동적 leeway로 24h 토큰도 cache HIT |
| quote_domestic --ticker 005930 현재가 | pass | 268,500원 (2026-05-10 21:16 KST 기준) |
| account --env mock_domestic 예수금/보유 | pass | 예수금 5억, 보유 0 |
| 005930 모의 1주 매수→매도 | skipped | 장외 시간 (장중 시간에 수동 검증 필요) |
| rate_limiter throttle (10 calls @4/sec ≥1.4s) | pass | 정확히 250ms 간격 측정 |
| secrets_loader 단위 테스트 (3건) | pass | parse + render + missing |
| tr_id_table 단위 테스트 (6건) | pass | 실/모의 차이, 선물 가드, 미등록 거부 |
| REAL_FUTURES 요청 시 KisError | pass | get_tr_id에서 `futures only supported in mock` |
| 401 응답 시 토큰 무효화 후 1회 재시도 | implemented | 코드 경로 존재, 실 401 발생 시점 미검증 |
| WebSocket approval key 200 OK | not yet | 골격만, MVP는 폴링 우선 |

추가:
- 5건 네트워크 스모크 (token, price, candles, orderbook, balance) 모두 PASS
- 12건 단위 테스트 (secrets×3, rate_limiter×3, tr_id×6) 모두 PASS

## 산출물

`app/kis/`:
- `exceptions.py`, `config.py`, `credentials.py`, `secrets_loader.py`
- `rate_limiter.py`, `tr_id_table.py`, `utils_paths.py`
- `auth.py`, `http.py`, `models.py`
- `quote_domestic.py`, `quote_overseas.py`
- `order_domestic.py`, `order_overseas.py`
- `account.py`, `futures.py`, `websocket.py`

`app/utils/`:
- `ticker.py` (KRX 6자리 ↔ yfinance 접미)
- `logging.py` (콘솔+파일 로거)

`scripts/`:
- `setup.ps1`, `run.ps1`, `test.ps1`, `migrate_secrets.ps1`

`tests/`:
- `test_kis_secrets_loader.py` (3건 PASS)
- `test_kis_rate_limiter.py` (3건 PASS)
- `test_kis_tr_id_table.py` (6건 PASS)
- `smoke_kis_mock.py` (5건 PASS, 1건 skipped)

`.kis_cache/token_mock_domestic.json` (gitignored)

`.env` (gitignored — MTS_API.txt에서 마이그레이션됨)
