# 설계 문서 — task-008-mobile-bridge (Flutter APK + FastAPI 백엔드)

> Status: ready
> Inputs: app/kis/ (Phase B), app/integrations/ta_runner.py (Phase C), collab.md 응답 (resolved)
> Outputs: app/api/main.py (FastAPI 게이트웨이), mobile/ (Flutter 앱), scripts/{start_api,start_tunnel,build_apk,install_apk}.ps1, mobile/build/app/outputs/flutter-apk/app-release.apk
> Next step: 사용자 검증 — 갤럭시에 APK 설치 후 LAN/Cloudflare Tunnel 통한 전체 동작 검증

## 목표 (Objective)

PC에서 동작하는 KIS+TradingAgents 백엔드를 안드로이드 갤럭시 폰에서 시세조회·잔고확인·주문·AI분석을 모두 수행할 수 있는 네이티브 APK로 노출. 사용자 본인만 사용, Play Store 미배포.

## 범위 (Scope)

- 포함:
  - FastAPI 게이트웨이 (`app/api/main.py`) — KIS 모듈 재사용, 인증 토큰, 실전 주문 PIN 검증
  - Flutter 앱 (`mobile/`) — 5 탭 (홈/시세/주문/AI/설정), 생체인증 + 다이얼로그 가드, secure storage
  - Cloudflare Quick Tunnel 안내 (외부 노출용)
  - APK 빌드/설치 스크립트
  - AI 분석 1시간 메모리 캐시 (LLM 비용 보호)
- 제외:
  - iOS 빌드 (사용자 갤럭시 사용)
  - Play Store 배포 / 코드 서명 정책 / Play Console
  - 푸시 알림 / 백그라운드 워커
  - 차트 인디케이터 패키지 (현재는 fl_chart 단순 라인)

## 제약 (Constraints)

- KIS 자격증명은 폰에 절대 저장하지 않음 — 백엔드 PC에만.
- 모바일 → 백엔드 인증: 헤더 `X-API-Token` (모든 엔드포인트), 실전 주문은 추가 `X-Real-PIN`.
- Android only (`flutter create --platforms android`).
- 빌드는 사용자 PC에서 수행 (Flutter SDK + Android SDK 36 + build-tools 36.0.0).
- 네트워크: LAN HTTP (8765 포트) 또는 Cloudflare Tunnel HTTPS.

## 구현 단계 (Implementation Steps)

1. `app/api/__init__.py`, `app/api/main.py` — FastAPI 인스턴스 + 인증 의존성 + 모든 엔드포인트
2. `pyproject.toml` 에 `fastapi`, `uvicorn[standard]` 추가
3. `.env`에 `MOBILE_API_TOKEN` 자동 생성 (32자 secrets.token_urlsafe)
4. Flutter 프로젝트 생성 — `flutter create --platforms android mobile`
5. `mobile/pubspec.yaml` 의존성: http, flutter_secure_storage, intl, fl_chart, local_auth, shared_preferences
6. `mobile/lib/api/{models,client}.dart` — Pydantic ↔ Dart 모델 + REST 클라이언트
7. `mobile/lib/services/secure_settings.dart` — Android Keystore 기반 설정 저장
8. `mobile/lib/main.dart` — Material 앱 + 다크 테마
9. `mobile/lib/pages/shell.dart` — 5 탭 NavigationBar + 라우터
10. `mobile/lib/pages/{home,quote,order,analysis,settings}.dart` — 각 페이지
11. `mobile/android/app/src/main/AndroidManifest.xml` — INTERNET, USE_BIOMETRIC permission
12. `scripts/{start_api,start_tunnel,build_apk,install_apk}.ps1` — 운영 스크립트
13. README 모바일 섹션 추가

## 파일/모듈 영향 (Affected Files/Modules)

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `app/api/__init__.py` | create | 빈 패키지 마커 |
| `app/api/main.py` | create | FastAPI 게이트웨이 (~270 LOC, 9 엔드포인트) |
| `pyproject.toml` | modify | fastapi, uvicorn 의존성 |
| `.env`, `.env.example` | modify | MOBILE_API_TOKEN, API_PORT 추가 |
| `mobile/` | create | Flutter 프로젝트 풀 트리 |
| `mobile/pubspec.yaml` | modify | http, secure_storage, fl_chart, local_auth |
| `mobile/lib/main.dart` | modify | 우리 앱으로 교체 |
| `mobile/lib/api/{models,client}.dart` | create | API 통신 |
| `mobile/lib/services/secure_settings.dart` | create | secure storage |
| `mobile/lib/pages/{shell,home,quote,order,analysis,settings}.dart` | create | UI 페이지 |
| `mobile/android/app/src/main/AndroidManifest.xml` | modify | permissions |
| `scripts/start_api.ps1` | create | uvicorn 실행 |
| `scripts/start_tunnel.ps1` | create | cloudflared 실행 |
| `scripts/build_apk.ps1` | create | release APK 빌드 |
| `scripts/install_apk.ps1` | create | adb install |

## 테스트 기준 (Test Criteria)

- [x] FastAPI 부팅 → `/health` HTTP 200 + `{"status":"ok"}`
- [x] `/quote/domestic/005930` 인증 없을 때 401, 토큰 있을 때 268,500원 응답
- [x] `/balance` (mock_domestic) 예수금 5억 응답
- [x] `flutter analyze` 에러 0 (style hint 4 + 예제 test 1 → fix 후 0)
- [x] `flutter build apk --release` 성공 → `app-release.apk` 생성
- [ ] 사용자: APK 갤럭시 설치 후 설정 → 백엔드 URL/토큰/PIN 입력 → 시세 조회 동작
- [ ] 사용자: 모의 주문 → 정상 응답
- [ ] 사용자: 실전 주문 → 생체인증 + 다이얼로그 + PIN 검증 모두 통과 후 체결

## 오픈 이슈 (Open Issues)

- Cloudflare Quick Tunnel은 무료지만 PC가 켜져있어야 폰이 접속 가능. 항상 가용은 아님.
- APK 서명 키는 자체 keystore (debug 키) — 폰 설정에서 "출처를 알 수 없는 앱" 허용 필요.
- 생체 인증 미지원 폰에서는 자동 fallback 다이얼로그만 사용.
- WebSocket 실시간 시세는 모바일에서 미구현 (REST 폴링 + 사용자 swipe-to-refresh).
- AI 분석 진행률 스트리밍은 모바일에서 미구현 (백엔드 응답 완료 후 결과만).
