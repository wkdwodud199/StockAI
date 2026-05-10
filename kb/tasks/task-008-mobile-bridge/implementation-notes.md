# 구현 노트 — task-008-mobile-bridge

> Status: in-progress (APK 빌드 + 사용자 폰 검증 대기)
> Inputs: kb/tasks/task-008-mobile-bridge/design.md
> Outputs: app/api/main.py, mobile/* (Flutter), scripts/*, .env MOBILE_API_TOKEN
> Next step: APK 빌드 완료 → 사용자가 갤럭시 설치 → 시세/주문 동작 확인 → done 전환

## 설계 대비 변경 사항

| 항목 | 설계 | 실제 | 사유 |
|------|------|------|------|
| 모바일 주문 정책 | 1차 인터뷰: read-only | 사용자 변경 요청으로 주문도 허용 | 가드(생체+다이얼로그+서버 PIN)로 위험 완화 |
| Android Studio 풀 설치 | 자동 설치 | 차단됨 (auto classifier) → 기존 사용자 SDK 활용 | 사용자 PC에 이미 SDK 36 cmdline-tools 존재 |
| Visual Studio 설치 | flutter doctor 권고 | 미설치 (APK는 Windows 빌드 불필요) | APK만 빌드 |
| Android licenses 자동 동의 | yes 자동 입력 | 차단됨 → 사용자 직접 동의 필요 | 라이선스는 사용자 동의 필요 |

## 구현 결정

1. **앱 위치 분리** — KIS/UI 코드는 `app/kis/`, FastAPI 게이트웨이는 `app/api/`, Flutter 앱은 `mobile/` (Python 패키지에서 제외).
2. **인증 분리** — 일반 엔드포인트는 `X-API-Token` 만, 실전 주문(`/order/buy/sell` + env=real_*)은 추가 `X-Real-PIN` 헤더 검증.
3. **Secure Storage** — 폰의 백엔드 URL/토큰/PIN을 `flutter_secure_storage` (Android Keystore 기반).
4. **AI 분석 캐시** — 같은 종목·날짜 1시간 동안 메모리 캐시 (LLM 비용 폭발 방지).
5. **모바일 dark 테마** — Material 3 + indigo seed.
6. **Cloudflare Tunnel** — 외부 노출 옵션. cloudflared 미설치 시 안내 메시지로 `winget install Cloudflare.cloudflared` 권고.

## 발생한 이슈

- Flutter doctor: build-tools 35.0.0의 aapt 누락 → build-tools 36.0.0 추가 설치로 해결.
- Android licenses 자동 동의 차단 (auto-classifier) → 사용자가 1회 직접 실행 필요.
- Default flutter create의 widget_test가 우리 클래스 이름과 안 맞음 → 단순화한 boot test로 교체.

## 테스트 결과 (현재 시점)

| 테스트 | 결과 |
|--------|------|
| FastAPI /health 200 | pass |
| /quote/domestic/005930 인증 없을 때 401 | pass |
| /quote/domestic/005930 토큰 헤더 시 268,500원 응답 | pass |
| /balance mock_domestic 5억 응답 | pass |
| flutter analyze 에러 0 | pass (style hint 4건만 남음, 빌드 영향 없음) |
| flutter build apk --release | (진행 중 — 노티 대기) |
| 사용자 폰 설치 후 시세 조회 | (사용자 검증) |
| 사용자 모의 주문 | (사용자 검증) |
| 사용자 실전 주문 (생체+PIN) | (사용자 검증) |

## 산출물

- `app/api/__init__.py`, `app/api/main.py` (~270 LOC)
- `mobile/pubspec.yaml` (의존성 8개)
- `mobile/lib/main.dart`, `mobile/lib/api/{models,client}.dart`, `mobile/lib/services/secure_settings.dart`
- `mobile/lib/pages/{shell,home,quote,order,analysis,settings}.dart` (~700 LOC)
- `mobile/test/widget_test.dart` (단순 boot test)
- `mobile/android/app/src/main/AndroidManifest.xml` (INTERNET, USE_BIOMETRIC, USE_FINGERPRINT)
- `scripts/{start_api,start_tunnel,build_apk,install_apk}.ps1`
- `.env` `MOBILE_API_TOKEN=Otn2iI8roa...` (랜덤 32자, 사용자 .env 직접 확인)
