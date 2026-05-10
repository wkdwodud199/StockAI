#requires -Version 5.1
<#
.SYNOPSIS
  Cloudflare Tunnel 임시 (Quick) Tunnel 시작. 무료 https URL을 발급받아 모바일 앱이 외부에서 접속할 수 있게 한다.
.NOTES
  cloudflared 미설치 시:
    winget install --id Cloudflare.cloudflared --accept-package-agreements --accept-source-agreements
.EXAMPLE
  .\scripts\start_tunnel.ps1
#>
param([int]$Port = 8765)

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Error @"
[tunnel] cloudflared 미설치.
  winget install --id Cloudflare.cloudflared
  또는 https://github.com/cloudflare/cloudflared/releases 에서 직접 다운로드.
"@
    exit 1
}

Write-Host "[tunnel] cloudflared tunnel --url http://localhost:$Port"
Write-Host "[tunnel] 출력 로그에서 'https://*.trycloudflare.com' 주소를 복사해 모바일 앱 설정에 입력하세요."
& cloudflared tunnel --url "http://localhost:$Port"
