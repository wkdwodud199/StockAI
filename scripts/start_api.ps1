#requires -Version 5.1
<#
.SYNOPSIS
  FastAPI 백엔드 (모바일 앱 게이트웨이) 실행. 기본 0.0.0.0:8765.
#>
param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

if (-not (Test-Path ".env")) {
    Write-Error "[api] .env 가 없습니다. .\scripts\setup.ps1 먼저 실행하세요."
    exit 1
}

Write-Host "[api] uvicorn app.api.main:app --host $Host --port $Port"
& .\.venv\Scripts\python.exe -m uvicorn app.api.main:app --host $Host --port $Port --proxy-headers
