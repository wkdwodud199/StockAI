#requires -Version 5.1
<#
.SYNOPSIS
  Flutter APK release 빌드. mobile/build/app/outputs/flutter-apk/app-release.apk 생성.
#>

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location "$root\mobile"

$flutter = "C:\dev\flutter\bin\flutter.bat"
if (-not (Test-Path $flutter)) {
    Write-Error "[apk] Flutter SDK 가 C:\dev\flutter 에 없습니다."
    exit 1
}

Write-Host "[apk] flutter pub get..."
& $flutter pub get

Write-Host "[apk] flutter build apk --release..."
& $flutter build apk --release

$apk = "$root\mobile\build\app\outputs\flutter-apk\app-release.apk"
if (Test-Path $apk) {
    Write-Host "[apk] OK: $apk"
    Write-Host "  연결된 폰에 설치하려면:  .\scripts\install_apk.ps1"
} else {
    Write-Error "[apk] 빌드 산출물이 없습니다."
    exit 1
}
