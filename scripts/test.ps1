#requires -Version 5.1
<#
.SYNOPSIS
  pytest 실행 (네트워크/실거래 마커는 기본 제외).
#>

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

& .\.venv\Scripts\python.exe -m pytest tests -m "not network and not real" $args
