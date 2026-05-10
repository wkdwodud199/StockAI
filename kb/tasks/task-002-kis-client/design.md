# 설계 문서 — task-002-kis-client (KIS Open API 클라이언트 라이브러리)

> Status: ready
> Inputs: typed-honking-kurzweil.md (마스터 플랜), MTS_API.txt (자격증명 - 소스 외부), KIS API 공식 문서 (https://apiportal.koreainvestment.com), https://github.com/koreainvestment/open-trading-api 샘플
> Outputs: app/kis/ 패키지 (auth, config, http, rate_limiter, quote_*, order_*, account, futures, websocket, models, exceptions, tr_id_table, secrets_loader, credentials), .kis_cache/ 토큰 캐시, scripts/migrate_secrets.ps1 동작, 모의 환경 스모크 테스트 스위트
> Next step: task-003-ta-adapter — 이 클라이언트가 노출하는 quote/account API를 TradingAgents dataflows로 브리지

## 목표 (Objective)

한국투자증권(KIS) Open API의 실전·모의·선물옵션 환경 3종을 단일 Python 패키지(`app/kis/`)에서 라우팅하고, OAuth 토큰 캐싱·환경별 레이트리미터·hashkey 자동 계산·TR_ID 자동 매핑을 통해 상위 모듈(Streamlit UI, TradingAgents 어댑터)이 환경 차이를 신경쓰지 않고 시세조회·주문·계좌조회를 호출할 수 있게 한다.

## 범위 (Scope)

- 포함:
  - OAuth2 토큰 발급 (POST /oauth2/tokenP) + 디스크 캐시 + day-80 자동 재발급
  - 환경 enum: REAL_DOMESTIC, MOCK_DOMESTIC, REAL_OVERSEAS, MOCK_OVERSEAS, MOCK_FUTURES
  - 환경별 base URL · TR_ID · rate-limit (real 15/sec, mock 4/sec, futures 별도) 라우팅
  - 국내주식 시세조회 (현재가, 호가, 일봉)
  - 해외주식 시세조회 (현재가)
  - 국내주식 매수/매도/취소/정정 + hashkey
  - 해외주식 매수/매도
  - 계좌 잔고·예수금·보유종목 조회 (국내/해외)
  - 국내 선물옵션 시세·주문 (모의 전용)
  - WebSocket approval key 발급 + 실시간 체결가 구독 골격 (MVP는 폴링 우선)
  - MTS_API.txt → .env 1회 마이그레이션 헬퍼
- 제외:
  - 채권·ELW·금현물·암호화폐 등 기타 상품
  - 주문 정정의 부분취소 등 고급 케이스 (1차 MVP는 전량 취소만)
  - 알고리즘 자동매매 엔진 (Phase C/D 영역)

## 제약 (Constraints)

- Python 3.11+ (현재 3.13.9 사용)
- 동기 `requests` 기반. asyncio는 WebSocket 모듈에서만
- `MTS_API.txt`의 자격증명은 절대 소스로 복사 금지. 1회 파싱 후 `.env`로 이관
- 모의 환경에서만 자동 스모크 테스트. 실전 호출은 사용자 수동 검증
- 모든 외부 호출은 환경별 토큰 버킷을 거치도록 강제 (전역 우회 금지)
- 토큰 캐시는 `.kis_cache/token_<env>.json` (gitignored)
- KIS 약관 호출 빈도 권장치 준수: 실전 ≤15 calls/sec, 모의 ≤4 calls/sec

## 구현 단계 (Implementation Steps)

1. `app/kis/exceptions.py` — `KisError`, `KisAuthError`, `KisRateLimitError`, `KisOrderRejected`, `KisHttpError` 정의
2. `app/kis/config.py` — `KisEnvironment` enum + `EnvConfig` dataclass (base_url, websocket_url, rate_per_sec, secret_env_keys)
3. `app/kis/credentials.py` — frozen dataclass `KisCredentials(app_key, app_secret, account_no, env)` + `from_env(env)` 팩토리
4. `app/kis/secrets_loader.py` — `MTS_API.txt` 정규식 파서 → 환경별 키/시크릿/계좌번호 추출 + `.env` 생성 헬퍼 + typer CLI (`migrate`)
5. `app/kis/rate_limiter.py` — `TokenBucket(rate, capacity)` 클래스, `acquire()` blocking. 환경별 싱글톤
6. `app/kis/auth.py` — `TokenStore` (디스크 JSON 캐시) + `get_access_token(env)` (cache hit/miss). day-80 자동 재발급. typer CLI
7. `app/kis/tr_id_table.py` — `{(operation, env): tr_id}` 룩업 테이블. 1차 entries: domestic-quote, domestic-orderbook, domestic-daily, domestic-buy, domestic-sell, domestic-cancel, domestic-amend, overseas-quote, overseas-buy, overseas-sell, balance-domestic, balance-overseas, futures-quote, futures-buy, futures-sell, hashkey
8. `app/kis/http.py` — `KisHttpClient(env)` 공통 클래스: `requests.Session` + 인증 헤더 자동 부착 + rate_limiter.acquire() 미들웨어 + 응답 코드 검사 (`rt_cd != "0"` → KisError)
9. `app/kis/models.py` — Pydantic 모델: `Quote`, `OrderBook`, `Candle`, `OrderResult`, `Holding`, `BalanceSummary`
10. `app/kis/quote_domestic.py` — `current_price(ticker)`, `orderbook(ticker)`, `daily_candles(ticker, start, end, period="D")` + typer CLI
11. `app/kis/quote_overseas.py` — `current_price(symbol, exchange="NAS")`
12. `app/kis/order_domestic.py` — `_make_hashkey(payload)` + `buy(ticker, qty, price=None)`, `sell(...)`, `cancel(order_no)`, `amend(...)`
13. `app/kis/order_overseas.py` — `buy(symbol, qty, price, exchange)`, `sell(...)`
14. `app/kis/account.py` — `inquire_balance(env)` → `BalanceSummary`, `inquire_holdings(env)` → `list[Holding]` + typer CLI
15. `app/kis/futures.py` — 모의 전용. `current_price(code)`, `buy(code, qty, price, ...)`, `sell(...)`
16. `app/kis/websocket.py` — `approval_key()` + `RealtimeStream(env, callback)` (asyncio, MVP 골격)
17. `app/utils/ticker.py` — 005930 ↔ 005930.KS ↔ 5930 정규화
18. `app/utils/logging.py` — 콘솔+파일 로거 (`.kis_cache/logs/kis-YYYYMMDD.log`)
19. `tests/test_kis_secrets_loader.py` — 가짜 텍스트 기반 단위 테스트
20. `tests/test_kis_rate_limiter.py` — 토큰 버킷 throttle 검증
21. `tests/test_kis_tr_id_table.py` — 환경×operation 라우팅 검증
22. `tests/smoke_kis_mock.py` — 모의 환경 통합 스모크 (수동 실행, pytest 마커 `@network`, `@slow`)

## 파일/모듈 영향 (Affected Files/Modules)

| 파일/모듈 | 변경 유형 | 설명 |
|-----------|-----------|------|
| `app/kis/__init__.py` | modify | 공개 API export (`get_client`, `KisEnvironment`) |
| `app/kis/exceptions.py` | create | 예외 계층 |
| `app/kis/config.py` | create | 환경 enum + URL/rate 라우팅 |
| `app/kis/credentials.py` | create | frozen 자격증명 dataclass |
| `app/kis/secrets_loader.py` | create | MTS_API.txt → .env 마이그레이터 |
| `app/kis/rate_limiter.py` | create | 환경별 토큰 버킷 |
| `app/kis/auth.py` | create | OAuth 토큰 발급/캐시/재발급 |
| `app/kis/tr_id_table.py` | create | TR_ID 룩업 테이블 |
| `app/kis/http.py` | create | requests 공통 클라이언트 |
| `app/kis/models.py` | create | Pydantic 응답 모델 |
| `app/kis/quote_domestic.py` | create | 국내 시세 |
| `app/kis/quote_overseas.py` | create | 해외 시세 |
| `app/kis/order_domestic.py` | create | 국내 주문 + hashkey |
| `app/kis/order_overseas.py` | create | 해외 주문 |
| `app/kis/account.py` | create | 잔고/보유 |
| `app/kis/futures.py` | create | 선물옵션 모의 전용 |
| `app/kis/websocket.py` | create | 실시간 스트림 골격 |
| `app/utils/ticker.py` | create | 종목코드 정규화 |
| `app/utils/logging.py` | create | 로거 |
| `tests/test_kis_secrets_loader.py` | create | 단위 테스트 |
| `tests/test_kis_rate_limiter.py` | create | 단위 테스트 |
| `tests/test_kis_tr_id_table.py` | create | 단위 테스트 |
| `tests/smoke_kis_mock.py` | create | 통합 스모크 (수동) |
| `.kis_cache/` | create | 토큰 캐시 디렉토리 (gitignored) |

## 테스트 기준 (Test Criteria)

- [x] `.\scripts\migrate_secrets.ps1` 후 `.env`에 5쌍 KEY/SECRET + 2개 계좌번호 채워짐
- [x] `python -m app.kis.auth --env mock_domestic` → access_token 출력 + `.kis_cache/token_mock_domestic.json` 생성
- [x] 동일 명령 재실행 시 캐시 HIT (네트워크 호출 없음)
- [x] `python -m app.kis.quote_domestic --ticker 005930` → 삼성전자 현재가 정수값 출력
- [x] `python -m app.kis.account --env mock_domestic` → 예수금 + 보유종목 출력
- [x] 모의에서 005930 1주 시장가 매수 → 주문번호 수신 → 즉시 매도 → 잔고 0 확인
- [x] `tests/test_kis_rate_limiter.py` 통과: 10 calls 시도 시 모의(rate=4)에서 ≥2.25초 소요
- [x] `tests/test_kis_secrets_loader.py` 통과: 가짜 텍스트로 5개 자격증명 파싱
- [x] 잘못된 환경 (REAL_FUTURES) 요청 시 `KisError("futures only supported in mock")` 발생
- [x] 401 응답 시 토큰 캐시 무효화 후 1회 재시도, 그래도 실패 시 `KisAuthError`
- [x] WebSocket approval key 발급은 모의에서 200 응답 확인까지만

## 오픈 이슈 (Open Issues)

- KIS 해외주식 base URL이 거래소(NAS/NYS/AMS)별로 분기되는지 1차 호출 시점 검증 필요
- 선물옵션 hashkey 생성 규칙이 주식과 동일한지 미확인 — 첫 주문 시 검증
- WebSocket 구독 ID 관리·재접속 정책은 후속 task로 분리
- `python-kis` 라이브러리는 dependency로 추가하지 않음 (라이선스/버전 결합도 최소화)
- `.env` 외에 OS keyring 사용 여부는 추후 사용자 요청 시 검토
