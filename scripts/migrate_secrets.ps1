#requires -Version 5.1
<#
.SYNOPSIS
  MTS_API.txt 의 KIS 자격증명을 .env 파일로 1회 마이그레이션.
.PARAMETER Source
  MTS_API.txt 경로. 기본값: $env:USERPROFILE\OneDrive\Desktop\MTS_API.txt
.PARAMETER Dest
  .env 출력 경로. 기본값: 프로젝트 루트의 .env
#>
param(
    [string]$Source = (Join-Path $env:USERPROFILE "OneDrive\Desktop\MTS_API.txt"),
    [string]$Dest = $null
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

if (-not $Dest) { $Dest = Join-Path $root ".env" }

if (-not (Test-Path $Source)) {
    Write-Error "[migrate] 자격증명 원본을 찾을 수 없습니다: $Source"
    exit 1
}

Write-Host "[migrate] $Source -> $Dest"
& .\.venv\Scripts\python.exe -m app.kis.secrets_loader migrate --src $Source --dest $Dest

Write-Host "[migrate] 완료. .env 파일을 확인하고 LLM API 키를 추가로 채우세요."
