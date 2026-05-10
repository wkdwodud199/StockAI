#requires -Version 5.1
<#
.SYNOPSIS
  장중 시간(평일 09:00~15:30 KST)에 KIS 모의 환경 005930 1주 매수→매도 라운드트립.
  장외 시간이면 안내 후 종료.
.EXAMPLE
  .\scripts\smoke_market_hours.ps1
#>

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

& .\.venv\Scripts\python.exe -X utf8 -c "@'
from datetime import datetime
from zoneinfo import ZoneInfo

now = datetime.now(ZoneInfo('Asia/Seoul'))
weekday = now.weekday()
if weekday >= 5:
    print(f'[skip] {now:%Y-%m-%d %H:%M %Z} 주말 — KRX 휴장')
    raise SystemExit(0)
if not (9 <= now.hour < 15) or (now.hour == 15 and now.minute > 30):
    print(f'[skip] {now:%Y-%m-%d %H:%M %Z} 장외 시간 — 09:00~15:30 KST 평일에 다시 시도')
    raise SystemExit(0)

from app.kis.config import KisEnvironment
from app.kis.quote_domestic import current_price
from app.kis.account import inquire_balance_domestic
from app.kis.order_domestic import buy, sell
from app.kis.exceptions import KisError

env = KisEnvironment.MOCK_DOMESTIC
print(f'[1/5] {now:%Y-%m-%d %H:%M %Z} 장중 — 라운드트립 시작')

print('[2/5] 005930 시세 조회')
q = current_price('005930', env=env)
print(f'  현재가 {q.price:,.0f}원')

print('[3/5] 매수 1주 (지정가)')
try:
    r1 = buy('005930', qty=1, price=q.price, env=env)
    print(f'  ODNO={r1.order_no} msg={r1.msg}')
except KisError as e:
    print(f'  매수 실패: {e}')
    raise SystemExit(1)

print('[4/5] 매도 1주 (지정가)')
try:
    r2 = sell('005930', qty=1, price=q.price, env=env)
    print(f'  ODNO={r2.order_no} msg={r2.msg}')
except KisError as e:
    print(f'  매도 실패: {e}')
    raise SystemExit(1)

print('[5/5] 잔고 조회')
b = inquire_balance_domestic(env=env)
print(f'  예수금 {b.deposit:,.0f}원, 보유 {len(b.holdings)}종목')
print('OK 라운드트립 완료')
'@" 2>&1
