#requires -Version 5.1
<#
.SYNOPSIS
  USB 디버깅이 활성화된 갤럭시에 APK 설치 (adb).
#>

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
$apk = "$root\mobile\build\app\outputs\flutter-apk\app-release.apk"

if (-not (Test-Path $apk)) {
    Write-Error "[install] APK 가 없습니다. .\scripts\build_apk.ps1 먼저 실행."
    exit 1
}

if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
    Write-Error "[install] adb 가 PATH 에 없습니다."
    exit 1
}

Write-Host "[install] 연결된 디바이스:"
& adb devices

Write-Host "[install] APK 설치..."
& adb install -r $apk

Write-Host "[install] 완료. 갤럭시 화면에서 'Stock MTS' 앱을 실행하세요."
