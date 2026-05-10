# Stock_MTS_TA

한국투자증권(KIS) Open API + [TradingAgents](https://github.com/TauricResearch/TradingAgents) 다중 에이전트 LLM 트레이딩 프레임워크를 통합한 데스크톱 트레이딩 앱.

- **UI**: Streamlit 웹 대시보드 (7 메뉴 — 홈 / 모의×3 / 실전×2 / AI)
- **거래 모드**: 모의/실전 분리 메뉴 (국내주식 · 해외주식 · 국내선물옵션[모의 전용])
- **AI 분석**: TradingAgents 다중 에이전트(Analysts → Researchers → Trader → Risk Mgmt → Portfolio Manager) 결과를 매매 의사결정 보조로 사용
- **워크플로우**: [Codex-With-Claude](https://github.com/wkdwodud199/Codex-With-Claude) 협업 프레임워크 — Codex가 `kb/tasks/<id>/design.md` 작성 → Claude가 구현

## 빠른 시작 (Windows PowerShell)

```powershell
# 한 번에 셋업: venv + TradingAgents clone + 의존성 + import 검증
.\scripts\setup.ps1

# 자격증명 설정 (MTS_API.txt가 있는 경우 자동 마이그레이션)
.\scripts\migrate_secrets.ps1
# 또는 수동: copy .env.example .env  ➜  편집

# 실행
.\scripts\run.ps1
# 브라우저: http://127.0.0.1:8501
```

수동 설치(setup.ps1 사용 안 할 때):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
git clone https://github.com/TauricResearch/TradingAgents.git TradingAgents
pip install -e .\TradingAgents
pip install -e ".[dev]"
```

## 디렉토리 구조

```
.
├── app/                            # 본 앱 코드 (commit됨)
│   ├── kis/                        # KIS Open API 클라이언트
│   ├── integrations/
│   │   ├── ta_dataflows/           # TradingAgents 호환 KIS dataflow 어댑터
│   │   ├── ta_kis_patch.py         # import-time monkey-patch (TA 포크 금지)
│   │   └── ta_runner.py            # propagate() 래퍼 + LLM provider 라우팅
│   ├── ui/                         # Streamlit 페이지
│   └── utils/
├── TradingAgents/                  # 외부 (gitignored, setup.ps1이 자동 클론)
├── kb/                             # Codex-With-Claude 지식베이스
├── runtime/                        # codex-design.ps1, claude-implement.ps1
├── templates/                      # design.md, implementation-notes.md, artifact-summary.md
├── scripts/                        # setup.ps1, run.ps1, test.ps1, migrate_secrets.ps1
├── tests/                          # pytest (단위 + network 마커)
├── pyproject.toml
└── .env.example
```

## LLM 공급자 설정

`.env` 또는 환경변수에 다음 중 하나만 채우면 됩니다:

```
LLM_PROVIDER=anthropic            # anthropic | openai | ollama
ANTHROPIC_API_KEY=sk-ant-...
# 또는 OPENAI_API_KEY=sk-...
# 또는 OLLAMA_BASE_URL=http://localhost:11434
```

분석 1회당 토큰은 모델/provider별로 다르지만 보통 $0.10~$1.00 수준입니다.

## 테스트

```powershell
.\scripts\test.ps1                 # 단위 테스트만 (network 마커 제외)
.\.venv\Scripts\python.exe -m pytest tests              # 전체 (네트워크 KIS 호출 포함)
.\.venv\Scripts\python.exe -m pytest tests -m network    # 네트워크 스모크만
```

## 보안

- `.env`, `MTS_API.txt`, `.kis_cache/`, `.venv/`, `TradingAgents/`는 `.gitignore`로 제외
- 실전 거래 메뉴는 4자리 PIN으로 잠금 (`REAL_MODE_PIN` 환경변수, 기본 `0000`)
- 매수/매도 실행 시 form-level 확인 체크박스 추가
- 선물옵션은 본 프로젝트에서 모의 전용 (실전 키 미보관)

## 모바일 (안드로이드, 본인 사용 전용)

Flutter 네이티브 앱 + FastAPI 백엔드. 갤럭시(또는 안드로이드 일반)에 APK 직접 설치 (Play Store 미배포).

```powershell
# 1) FastAPI 백엔드 시작 (PC)
.\scripts\start_api.ps1
# → http://0.0.0.0:8765

# 2) 외부 노출 (옵션) — 갤럭시가 LAN 바깥에서 접속 가능하도록
.\scripts\start_tunnel.ps1
# 출력 https://*.trycloudflare.com 주소를 복사

# 3) APK 빌드 (Flutter SDK 필요. setup.ps1 자동 안내 또는 git clone)
.\scripts\build_apk.ps1
# → mobile/build/app/outputs/flutter-apk/app-release.apk

# 4) USB 연결된 갤럭시에 설치
.\scripts\install_apk.ps1
```

앱 첫 실행 시 설정 화면:
- **백엔드 URL**: cloudflared 출력 또는 LAN의 `http://192.168.x.x:8765`
- **API 토큰**: `.env` 의 `MOBILE_API_TOKEN` 값
- **실전 PIN**: `.env` 의 `REAL_MODE_PIN` (실전 주문 시 헤더에 첨부)

모바일 실전 주문은 다음 가드를 모두 통과해야 실행됨:
1. 클라이언트: 생체 인증 (지문/얼굴) — 가능한 디바이스에서만
2. 클라이언트: 확인 다이얼로그
3. 클라이언트: 헤더 `X-Real-PIN` 자동 첨부
4. 서버: PIN 일치 검증 (`require_real_pin`)

## 라이선스

본 저장소의 코드(앱)는 사용자 작성. TradingAgents는 Apache 2.0, KIS API 사용은 한국투자증권 약관 준수.
