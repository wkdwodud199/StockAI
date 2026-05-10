"""국내 선물옵션 — 모의 전용.

KIS의 선물옵션 API는 주식과 별도 엔드포인트·TR_ID 사용.
실전 거래 환경 키는 본 프로젝트에 보관하지 않음 (모의 키만 사용).
"""

from __future__ import annotations

import typer

from app.kis.config import KisEnvironment, parse_env
from app.kis.exceptions import KisError
from app.kis.http import KisHttpClient
from app.kis.models import OrderResult, Quote
from app.kis.tr_id_table import get_tr_id


def _ensure_mock(env: KisEnvironment) -> None:
    if env is not KisEnvironment.MOCK_FUTURES:
        raise KisError(f"futures only supported in MOCK_FUTURES (got {env.value})")


def current_price(code: str, env: KisEnvironment = KisEnvironment.MOCK_FUTURES) -> Quote:
    _ensure_mock(env)
    client = KisHttpClient(env)
    data = client.get(
        "/uapi/domestic-futureoption/v1/quotations/inquire-price",
        tr_id=get_tr_id("futures-quote", env),
        params={
            "FID_COND_MRKT_DIV_CODE": "F",
            "FID_INPUT_ISCD": code,
        },
    )
    out = data.get("output1", {}) or data.get("output", {}) or {}

    def _f(k: str) -> float:
        try:
            v = out.get(k)
            return float(v) if v not in (None, "") else 0.0
        except (TypeError, ValueError):
            return 0.0

    return Quote(
        ticker=code,
        price=_f("futs_prpr") or _f("stck_prpr") or _f("last"),
        change=_f("futs_prdy_vrss") or _f("prdy_vrss"),
        change_pct=_f("futs_prdy_ctrt") or _f("prdy_ctrt"),
        volume=int(_f("acml_vol")),
        raw=out,
    )


def buy(code: str, qty: int, price: float, env: KisEnvironment = KisEnvironment.MOCK_FUTURES) -> OrderResult:
    _ensure_mock(env)
    client = KisHttpClient(env)
    creds = client.creds
    body = {
        "ORD_PRCS_DVSN_CD": "02",
        "CANO": creds.account_prefix,
        "ACNT_PRDT_CD": creds.account_suffix,
        "SLL_BUY_DVSN_CD": "02",  # 02=매수
        "SHTN_PDNO": code,
        "ORD_QTY": str(qty),
        "UNIT_PRICE": f"{price:.2f}",
        "NMPR_TYPE_CD": "",
        "KRX_NMPR_CNDT_CD": "",
        "ORD_DVSN_CD": "01",  # 01=지정가
    }
    tr_id = get_tr_id("futures-buy", env)
    hash_h = client.hashkey(body)
    data = client.post(
        "/uapi/domestic-futureoption/v1/trading/order",
        tr_id=tr_id, body=body, extra_headers={"hashkey": hash_h},
    )
    out = data.get("output", {}) or {}
    return OrderResult(
        success=True,
        order_no=out.get("ODNO") or out.get("odno"),
        msg_cd=data.get("msg_cd", ""),
        msg=data.get("msg1", ""),
        raw=data,
    )


def sell(code: str, qty: int, price: float, env: KisEnvironment = KisEnvironment.MOCK_FUTURES) -> OrderResult:
    _ensure_mock(env)
    client = KisHttpClient(env)
    creds = client.creds
    body = {
        "ORD_PRCS_DVSN_CD": "02",
        "CANO": creds.account_prefix,
        "ACNT_PRDT_CD": creds.account_suffix,
        "SLL_BUY_DVSN_CD": "01",  # 01=매도
        "SHTN_PDNO": code,
        "ORD_QTY": str(qty),
        "UNIT_PRICE": f"{price:.2f}",
        "NMPR_TYPE_CD": "",
        "KRX_NMPR_CNDT_CD": "",
        "ORD_DVSN_CD": "01",
    }
    tr_id = get_tr_id("futures-sell", env)
    hash_h = client.hashkey(body)
    data = client.post(
        "/uapi/domestic-futureoption/v1/trading/order",
        tr_id=tr_id, body=body, extra_headers={"hashkey": hash_h},
    )
    out = data.get("output", {}) or {}
    return OrderResult(
        success=True,
        order_no=out.get("ODNO") or out.get("odno"),
        msg_cd=data.get("msg_cd", ""),
        msg=data.get("msg1", ""),
        raw=data,
    )


app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def price(code: str = typer.Option(..., "--code", help="예: 101W3000 (KOSPI200 선물 근월물)")) -> None:
    q = current_price(code)
    typer.echo(f"{q.ticker}  현재={q.price:,.2f}  Δ={q.change:+.2f} ({q.change_pct:+.2f}%)  vol={q.volume:,}")


if __name__ == "__main__":
    app()
