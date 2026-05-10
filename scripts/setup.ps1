#requires -Version 5.1
<#
.SYNOPSIS
  Stock_MTS_TA 초기 환경 세팅 — venv 생성, 의존성 설치, .env 검증.
.EXAMPLE
  .\scripts\setup.ps1
#>

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

if (-not (Test-Path ".venv")) {
    Write-Host "[setup] venv 생성..."
    python -m venv .venv
}

Write-Host "[setup] pip 업그레이드..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null

if (-not (Test-Path "TradingAgents\pyproject.toml")) {
    Write-Host "[setup] TradingAgents 클론 (TauricResearch/TradingAgents)..."
    git clone https://github.com/TauricResearch/TradingAgents.git TradingAgents
} else {
    Write-Host "[setup] TradingAgents 디렉토리 발견."
}

Write-Host "[setup] TradingAgents 설치 (pip install -e ./TradingAgents)..."
& .\.venv\Scripts\python.exe -m pip install -e .\TradingAgents

Write-Host "[setup] 본 앱 설치 (pip install -e .[dev])..."
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

if (-not (Test-Path ".env")) {
    Write-Host "[setup] .env 파일이 없습니다. .env.example을 복사한 뒤 KIS 자격증명을 채우세요."
    Write-Host "        또는: .\scripts\migrate_secrets.ps1 실행"
} else {
    Write-Host "[setup] .env 발견."
}

Write-Host "[setup] 검증: import tradingagents"
& .\.venv\Scripts\python.exe -c "import tradingagents; print('OK', tradingagents.__name__)"

Write-Host "[setup] 완료."
