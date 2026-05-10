#requires -Version 5.1
<#
.SYNOPSIS
  Streamlit 대시보드 실행.
#>

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

if (-not (Test-Path ".env")) {
    Write-Error "[run] .env 가 없습니다. .\scripts\setup.ps1 먼저 실행하세요."
    exit 1
}

if (-not (Test-Path "app\ui\streamlit_app.py")) {
    Write-Error "[run] app\ui\streamlit_app.py 가 없습니다. Phase D 구현 후 실행하세요."
    exit 1
}

& .\.venv\Scripts\python.exe -m streamlit run app\ui\streamlit_app.py
