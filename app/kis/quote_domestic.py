"""국내주식 시세 조회 — 현재가, 호가, 일봉."""

from __future__ import annotations

from datetime import date
from typing import Any

import typer

from app.kis.config import KisEnvironment, parse_env
from app.kis.http import KisHttpClient
from app.kis.models import Candle, OrderBook, OrderBookLevel, Quote
from app.kis.tr_id_table import get_tr_id
from app.utils.ticker import to_krx


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "NaN") else default
    except (TypeError, ValueError):
        return default


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v)) if v not in (None, "", "NaN") else default
    except (TypeError, ValueError):
        return default


def current_price(ticker: str, env: KisEnvironment = KisEnvironment.MOCK_DOMESTIC) -> Quote:
    code = to_krx(ticker)
    client = KisHttpClient(env)
    data = client.get(
        "/uapi/domestic-stock/v1/quotations/inquire-price",
        tr_id=get_tr_id("domestic-quote", env),
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code,
        },
    )
    out = data.get("output", {})
    return Quote(
        ticker=code,
        price=_to_float(out.get("stck_prpr")),
        change=_to_float(out.get("prdy_vrss")),
        change_pct=_to_float(out.get("prdy_ctrt")),
        volume=_to_int(out.get("acml_vol")),
        high=_to_float(out.get("stck_hgpr")),
        low=_to_float(out.get("stck_lwpr")),
        open=_to_float(out.get("stck_oprc")),
        prev_close=_to_float(out.get("stck_sdpr")),
        raw=out,
    )


def orderbook(ticker: str, env: KisEnvironment = KisEnvironment.MOCK_DOMESTIC) -> OrderBook:
    code = to_krx(ticker)
    client = KisHttpClient(env)
    data = client.get(
        "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn",
        tr_id=get_tr_id("domestic-orderbook", env),
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code,
        },
    )
    out1 = data.get("output1", {}) if isinstance(data.get("output1"), dict) else {}
    bids: list[OrderBookLevel] = []
    asks: list[OrderBookLevel] = []
    for i in range(1, 11):
        bp = _to_float(out1.get(f"bidp{i}"))
        bq = _to_int(out1.get(f"bidp_rsqn{i}"))
        ap = _to_float(out1.get(f"askp{i}"))
        aq = _to_int(out1.get(f"askp_rsqn{i}"))
        if bp > 0:
            bids.append(OrderBookLevel(price=bp, qty=bq))
        if ap > 0:
            asks.append(OrderBookLevel(price=ap, qty=aq))
    return OrderBook(ticker=code, bids=bids, asks=asks, raw=out1)


def daily_candles(
    ticker: str,
    start: date,
    end: date,
    *,
    period: str = "D",
    adjusted: bool = True,
    env: KisEnvironment = KisEnvironment.MOCK_DOMESTIC,
) -> list[Candle]:
    code = to_krx(ticker)
    client = KisHttpClient(env)
    data = client.get(
        "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
        tr_id=get_tr_id("domestic-daily", env),
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code,
            "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": period,
            "FID_ORG_ADJ_PRC": "0" if adjusted else "1",
        },
    )
    rows = data.get("output2", []) or []
    candles: list[Candle] = []
    for row in rows:
        d_str = row.get("stck_bsop_date")
        if not d_str:
            continue
        try:
            d = date.fromisoformat(f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}")
        except ValueError:
            continue
        candles.append(
            Candle(
                date=d,
                open=_to_float(row.get("stck_oprc")),
                high=_to_float(row.get("stck_hgpr")),
                low=_to_float(row.get("stck_lwpr")),
                close=_to_float(row.get("stck_clpr")),
                volume=_to_int(row.get("acml_vol")),
            )
        )
    candles.sort(key=lambda c: c.date)
    return candles


# ---------- typer CLI ----------
app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def price(
    ticker: str = typer.Option(..., "--ticker", help="6자리 KRX 코드 (예: 005930)"),
    env: str = typer.Option("mock_domestic", "--env"),
) -> None:
    e = parse_env(env)
    q = current_price(ticker, env=e)
    typer.echo(
        f"{q.ticker}  현재가={q.price:,.0f}  전일대비={q.change:+,.0f} ({q.change_pct:+.2f}%)  "
        f"거래량={q.volume:,}  고가={q.high:,.0f}  저가={q.low:,.0f}"
    )


@app.command()
def book(
    ticker: str = typer.Option(..., "--ticker"),
    env: str = typer.Option("mock_domestic", "--env"),
) -> None:
    e = parse_env(env)
    ob = orderbook(ticker, env=e)
    typer.echo(f"{ob.ticker} 호가 (10단)")
    for i, lvl in enumerate(ob.asks[::-1], 1):
        typer.echo(f"  매도{11-i:>2}  {lvl.price:>10,.0f}  {lvl.qty:>10,}")
    typer.echo("  ---------- 체결 ----------")
    for i, lvl in enumerate(ob.bids, 1):
        typer.echo(f"  매수{i:>2}  {lvl.price:>10,.0f}  {lvl.qty:>10,}")


if __name__ == "__main__":
    app()
