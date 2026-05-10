"""해외주식 매수/매도."""

from __future__ import annotations

import typer

from app.kis.config import KisEnvironment, parse_env
from app.kis.http import KisHttpClient
from app.kis.models import OrderResult, OrderSide, OrderType
from app.kis.tr_id_table import get_tr_id

# KIS 해외 주문 API의 거래소 코드 (시세 EXCD와 다름)
_EXCG_MAP = {
    "NAS": "NASD",
    "NYS": "NYSE",
    "AMS": "AMEX",
    "HKS": "SEHK",
    "TSE": "TKSE",
}


def _place(
    side: OrderSide,
    symbol: str,
    qty: int,
    price: float,
    *,
    exchange: str = "NAS",
    order_type: OrderType = "limit",
    env: KisEnvironment = KisEnvironment.MOCK_OVERSEAS,
) -> OrderResult:
    excg = _EXCG_MAP.get(exchange.upper(), exchange.upper())
    client = KisHttpClient(env)
    creds = client.creds

    body = {
        "CANO": creds.account_prefix,
        "ACNT_PRDT_CD": creds.account_suffix,
        "OVRS_EXCG_CD": excg,
        "PDNO": symbol.strip().upper(),
        "ORD_QTY": str(qty),
        "OVRS_ORD_UNPR": f"{price:.4f}",
        "ORD_SVR_DVSN_CD": "0",
        "ORD_DVSN": "00" if order_type == "limit" else "01",
    }
    op = "overseas-buy" if side == "buy" else "overseas-sell"
    tr_id = get_tr_id(op, env)
    hash_h = client.hashkey(body)
    data = client.post(
        "/uapi/overseas-stock/v1/trading/order",
        tr_id=tr_id,
        body=body,
        extra_headers={"hashkey": hash_h},
    )
    out = data.get("output", {}) or {}
    return OrderResult(
        success=True,
        order_no=out.get("ODNO") or out.get("odno"),
        krx_fwdg_ord_orgno=out.get("KRX_FWDG_ORD_ORGNO"),
        ord_tmd=out.get("ORD_TMD"),
        msg_cd=data.get("msg_cd", ""),
        msg=data.get("msg1", ""),
        raw=data,
    )


def buy(
    symbol: str, qty: int, price: float, *,
    exchange: str = "NAS", env: KisEnvironment = KisEnvironment.MOCK_OVERSEAS,
) -> OrderResult:
    return _place("buy", symbol, qty, price, exchange=exchange, env=env)


def sell(
    symbol: str, qty: int, price: float, *,
    exchange: str = "NAS", env: KisEnvironment = KisEnvironment.MOCK_OVERSEAS,
) -> OrderResult:
    return _place("sell", symbol, qty, price, exchange=exchange, env=env)


app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("buy")
def cli_buy(
    symbol: str = typer.Option(..., "--symbol"),
    qty: int = typer.Option(..., "--qty"),
    price: float = typer.Option(..., "--price"),
    exchange: str = typer.Option("NAS", "--exchange"),
    env: str = typer.Option("mock_overseas", "--env"),
) -> None:
    e = parse_env(env)
    r = buy(symbol, qty, price, exchange=exchange, env=e)
    typer.echo(f"BUY {symbol}@{exchange} qty={qty} price=${price} → ODNO={r.order_no} msg={r.msg}")


@app.command("sell")
def cli_sell(
    symbol: str = typer.Option(..., "--symbol"),
    qty: int = typer.Option(..., "--qty"),
    price: float = typer.Option(..., "--price"),
    exchange: str = typer.Option("NAS", "--exchange"),
    env: str = typer.Option("mock_overseas", "--env"),
) -> None:
    e = parse_env(env)
    r = sell(symbol, qty, price, exchange=exchange, env=e)
    typer.echo(f"SELL {symbol}@{exchange} qty={qty} price=${price} → ODNO={r.order_no} msg={r.msg}")


if __name__ == "__main__":
    app()
