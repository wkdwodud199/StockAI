# 산출물 요약 — task-008-mobile-bridge

> Status: in-progress (APK 빌드/사용자 검증 대기)
> Inputs: kb/tasks/task-008-mobile-bridge/implementation-notes.md
> Outputs: 본 요약
> Next step: 사용자 갤럭시 설치 + 동작 검증

## 작업 요약

- **Task ID**: task-008-mobile-bridge
- **제목**: Flutter Android APK + FastAPI 게이트웨이 (사용자 본인 사용 전용)
- **시작일**: 2026-05-10

## 산출물

| 산출물 | 경로 | 설명 |
|--------|------|------|
| FastAPI 게이트웨이 | `app/api/main.py` | KIS 엔드포인트 9개 + 인증 + AI 분석 캐시 |
| Flutter 앱 | `mobile/` | 5 탭 (홈/시세/주문/AI/설정), Material 3 dark |
| 모바일 secure storage | `mobile/lib/services/secure_settings.dart` | Android Keystore 기반 |
| 운영 스크립트 | `scripts/{start_api,start_tunnel,build_apk,install_apk}.ps1` | 백엔드/터널/빌드/설치 자동화 |
| README 모바일 섹션 | `README.md` | 사용 절차 + 인증 가드 안내 |

## 주요 결정

- **모바일도 주문 가능 (사용자 요청)** + 3단계 가드: 생체인증 → 다이얼로그 → 서버 PIN.
- **자격증명은 폰에 저장 안 함** — KIS 키는 백엔드 PC에만, 폰은 우리 토큰만 보유.
- **TradingAgents 분석 1시간 메모리 캐시** — LLM 비용 보호.
- **Cloudflare Quick Tunnel** — 외부 접속 옵션, cloudflared는 사용자가 winget으로 설치.
- **Android Studio 풀 설치 회피** — 사용자 PC의 기존 SDK 활용 (auto-classifier 차단 회피).

## 검증 evidence (백엔드 측)

```
$ uvicorn app.api.main:app --host 0.0.0.0 --port 8765
$ curl -H "X-API-Token: Otn2iI8roa..." http://localhost:8765/quote/domestic/005930?env=mock_domestic
{"ticker":"005930","price":268500.0,"change":-3000.0,...}

$ curl -H "X-API-Token: Otn2iI8roa..." http://localhost:8765/balance
{"deposit":500000000.0,"eval_total":500000000.0,...}

$ curl http://localhost:8765/quote/domestic/005930  # without token
HTTP 401 invalid X-API-Token
```

## 사용자 다음 단계

1. **Android licenses 동의** (1회):
   ```powershell
   C:\dev\flutter\bin\flutter doctor --android-licenses
   ```
   y 반복 입력으로 동의.

2. **APK 빌드 완료 대기 + 갤럭시 USB 연결**:
   ```powershell
   .\scripts\install_apk.ps1
   ```

3. **앱 첫 실행**:
   - 백엔드 URL: cloudflared 출력 또는 `http://192.168.x.x:8765`
   - API 토큰: `.env` 의 `MOBILE_API_TOKEN`
   - 실전 PIN: `.env` 의 `REAL_MODE_PIN`

4. 시세/잔고/모의 주문 → 정상 동작 확인 후 task-008 status: done 전환.

## 관련 문서

- 설계: `kb/tasks/task-008-mobile-bridge/design.md`
- 구현 노트: `kb/tasks/task-008-mobile-bridge/implementation-notes.md`
- collab.md: request-changes 일괄 resolved 응답 포함
