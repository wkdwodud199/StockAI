"""국내주식 매수/매도/취소/정정.

핵심:
- ORD_DVSN: "00" 지정가, "01" 시장가, "07" 시간외단일가 등
- 주문/취소/정정은 hashkey 헤더 필요
- 응답의 KRX_FWDG_ORD_ORGNO + ODNO 가 정정/취소 시 필수
"""

from __future__ import annotations

from typing import Literal

import typer

from app.kis.config import KisEnvironment, parse_env
from app.kis.http import KisHttpClient
from app.kis.models import OrderResult, OrderSide, OrderType
from app.kis.tr_id_table import get_tr_id
from app.utils.ticker import to_krx


def _place(
    side: OrderSide,
    ticker: str,
    qty: int,
    price: float | None = None,
    *,
    order_type: OrderType = "limit",
    env: KisEnvironment = KisEnvironment.MOCK_DOMESTIC,
) -> OrderResult:
    code = to_krx(ticker)
    client = KisHttpClient(env)
    creds = client.creds

    if order_type == "market":
        ord_dvsn = "01"
        ord_unpr = "0"
    else:
        ord_dvsn = "00"
        if price is None or price <= 0:
            raise ValueError("limit order requires positive price")
        ord_unpr = str(int(price))  # KRX 호가 단위는 정수

    body = {
        "CANO": creds.account_prefix,
        "ACNT_PRDT_CD": creds.account_suffix,
        "PDNO": code,
        "ORD_DVSN": ord_dvsn,
        "ORD_QTY": str(qty),
        "ORD_UNPR": ord_unpr,
    }
    op = "domestic-buy" if side == "buy" else "domestic-sell"
    tr_id = get_tr_id(op, env)
    hash_h = client.hashkey(body)
    data = client.post(
        "/uapi/domestic-stock/v1/trading/order-cash",
        tr_id=tr_id,
        body=body,
        extra_headers={"hashkey": hash_h},
    )
    out = data.get("output", {}) or {}
    return OrderResult(
        success=True,
        order_no=out.get("ODNO") or out.get("odno"),
        krx_fwdg_ord_orgno=out.get("KRX_FWDG_ORD_ORGNO") or out.get("krx_fwdg_ord_orgno"),
        ord_tmd=out.get("ORD_TMD") or out.get("ord_tmd"),
        msg_cd=data.get("msg_cd", ""),
        msg=data.get("msg1", ""),
        raw=data,
    )


def buy(
    ticker: str,
    qty: int,
    price: float | None = None,
    *,
    order_type: OrderType = "limit",
    env: KisEnvironment = KisEnvironment.MOCK_DOMESTIC,
) -> OrderResult:
    return _place("buy", ticker, qty, price, order_type=order_type, env=env)


def sell(
    ticker: str,
    qty: int,
    price: float | None = None,
    *,
    order_type: OrderType = "limit",
    env: KisEnvironment = KisEnvironment.MOCK_DOMESTIC,
) -> OrderResult:
    return _place("sell", ticker, qty, price, order_type=order_type, env=env)


def cancel(
    krx_fwdg_ord_orgno: str,
    order_no: str,
    *,
    env: KisEnvironment = KisEnvironment.MOCK_DOMESTIC,
) -> OrderResult:
    """원주문 전량 취소."""
    client = KisHttpClient(env)
    creds = client.creds
    body = {
        "CANO": creds.account_prefix,
        "ACNT_PRDT_CD": creds.account_suffix,
        "KRX_FWDG_ORD_ORGNO": krx_fwdg_ord_orgno,
        "ORGN_ODNO": order_no,
        "ORD_DVSN": "00",
        "RVSE_CNCL_DVSN_CD": "02",
        "ORD_QTY": "0",
        "ORD_UNPR": "0",
        "QTY_ALL_ORD_YN": "Y",
    }
    tr_id = get_tr_id("domestic-cancel", env)
    hash_h = client.hashkey(body)
    data = client.post(
        "/uapi/domestic-stock/v1/trading/order-rvsecncl",
        tr_id=tr_id,
        body=body,
        extra_headers={"hashkey": hash_h},
    )
    out = data.get("output", {}) or {}
    return OrderResult(
        success=True,
        order_no=out.get("ODNO") or out.get("odno"),
        msg_cd=data.get("msg_cd", ""),
        msg=data.get("msg1", ""),
        raw=data,
    )


def amend(
    krx_fwdg_ord_orgno: str,
    order_no: str,
    new_price: float,
    qty: int,
    *,
    env: KisEnvironment = KisEnvironment.MOCK_DOMESTIC,
) -> OrderResult:
    """원주문 가격/수량 정정."""
    client = KisHttpClient(env)
    creds = client.creds
    body = {
        "CANO": creds.account_prefix,
        "ACNT_PRDT_CD": creds.account_suffix,
        "KRX_FWDG_ORD_ORGNO": krx_fwdg_ord_orgno,
        "ORGN_ODNO": order_no,
        "ORD_DVSN": "00",
        "RVSE_CNCL_DVSN_CD": "01",
        "ORD_QTY": str(qty),
        "ORD_UNPR": str(int(new_price)),
        "QTY_ALL_ORD_YN": "N",
    }
    tr_id = get_tr_id("domestic-amend", env)
    hash_h = client.hashkey(body)
    data = client.post(
        "/uapi/domestic-stock/v1/trading/order-rvsecncl",
        tr_id=tr_id,
        body=body,
        extra_headers={"hashkey": hash_h},
    )
    out = data.get("output", {}) or {}
    return OrderResult(
        success=True,
        order_no=out.get("ODNO") or out.get("odno"),
        msg_cd=data.get("msg_cd", ""),
        msg=data.get("msg1", ""),
        raw=data,
    )


# ---------- typer CLI ----------
app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("buy")
def cli_buy(
    ticker: str = typer.Option(..., "--ticker"),
    qty: int = typer.Option(..., "--qty"),
    price: float | None = typer.Option(None, "--price", help="시장가는 생략"),
    env: str = typer.Option("mock_domestic", "--env"),
) -> None:
    e = parse_env(env)
    order_type: Literal["market", "limit"] = "market" if price is None else "limit"
    r = buy(ticker, qty, price, order_type=order_type, env=e)
    typer.echo(f"BUY {ticker} qty={qty} price={price} → ODNO={r.order_no} msg={r.msg}")


@app.command("sell")
def cli_sell(
    ticker: str = typer.Option(..., "--ticker"),
    qty: int = typer.Option(..., "--qty"),
    price: float | None = typer.Option(None, "--price"),
    env: str = typer.Option("mock_domestic", "--env"),
) -> None:
    e = parse_env(env)
    order_type: Literal["market", "limit"] = "market" if price is None else "limit"
    r = sell(ticker, qty, price, order_type=order_type, env=e)
    typer.echo(f"SELL {ticker} qty={qty} price={price} → ODNO={r.order_no} msg={r.msg}")


if __name__ == "__main__":
    app()
