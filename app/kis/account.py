"""계좌 잔고/보유종목 조회 (국내·해외)."""

from __future__ import annotations

from typing import Any

import typer

from app.kis.config import KisEnvironment, parse_env
from app.kis.http import KisHttpClient
from app.kis.models import BalanceSummary, Holding
from app.kis.tr_id_table import get_tr_id


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _i(v: Any, default: int = 0) -> int:
    try:
        return int(float(v)) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def inquire_balance_domestic(env: KisEnvironment = KisEnvironment.MOCK_DOMESTIC) -> BalanceSummary:
    client = KisHttpClient(env)
    creds = client.creds
    params = {
        "CANO": creds.account_prefix,
        "ACNT_PRDT_CD": creds.account_suffix,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    data = client.get(
        "/uapi/domestic-stock/v1/trading/inquire-balance",
        tr_id=get_tr_id("balance-domestic", env),
        params=params,
    )

    holdings: list[Holding] = []
    for row in data.get("output1", []) or []:
        qty = _i(row.get("hldg_qty"))
        if qty <= 0:
            continue
        holdings.append(
            Holding(
                ticker=row.get("pdno", "") or "",
                name=row.get("prdt_name", "") or "",
                qty=qty,
                avg_price=_f(row.get("pchs_avg_pric")),
                current_price=_f(row.get("prpr")),
                eval_amt=_f(row.get("evlu_amt")),
                pnl=_f(row.get("evlu_pfls_amt")),
                pnl_pct=_f(row.get("evlu_pfls_rt")),
            )
        )

    out2 = (data.get("output2") or [{}])[0] if isinstance(data.get("output2"), list) else {}
    return BalanceSummary(
        deposit=_f(out2.get("dnca_tot_amt")),
        eval_total=_f(out2.get("tot_evlu_amt")),
        pnl_total=_f(out2.get("evlu_pfls_smtl_amt")),
        holdings=holdings,
    )


def inquire_balance_overseas(env: KisEnvironment = KisEnvironment.MOCK_OVERSEAS) -> BalanceSummary:
    client = KisHttpClient(env)
    creds = client.creds
    # 미국 NASD 기본
    params = {
        "CANO": creds.account_prefix,
        "ACNT_PRDT_CD": creds.account_suffix,
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": "",
    }
    data = client.get(
        "/uapi/overseas-stock/v1/trading/inquire-balance",
        tr_id=get_tr_id("balance-overseas", env),
        params=params,
    )
    holdings: list[Holding] = []
    for row in data.get("output1", []) or []:
        qty = _i(row.get("ovrs_cblc_qty"))
        if qty <= 0:
            continue
        holdings.append(
            Holding(
                ticker=row.get("ovrs_pdno", "") or "",
                name=row.get("ovrs_item_name", "") or "",
                qty=qty,
                avg_price=_f(row.get("pchs_avg_pric")),
                current_price=_f(row.get("now_pric2") or row.get("ovrs_now_pric1")),
                eval_amt=_f(row.get("ovrs_stck_evlu_amt")),
                pnl=_f(row.get("frcr_evlu_pfls_amt")),
                pnl_pct=_f(row.get("evlu_pfls_rt")),
            )
        )
    out2 = data.get("output2", {}) or {}
    return BalanceSummary(
        deposit=_f(out2.get("frcr_buy_amt_smtl1")),
        eval_total=_f(out2.get("tot_evlu_pfls_amt")),
        pnl_total=_f(out2.get("evlu_pfls_amt_smtl")),
        holdings=holdings,
    )


def inquire_balance(env: KisEnvironment) -> BalanceSummary:
    if env.is_overseas:
        return inquire_balance_overseas(env)
    return inquire_balance_domestic(env)


app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def balance(env: str = typer.Option("mock_domestic", "--env")) -> None:
    e = parse_env(env)
    summary = inquire_balance(e)
    typer.echo(f"=== {e.value} ===")
    typer.echo(f"예수금: {summary.deposit:,.0f}")
    typer.echo(f"평가총액: {summary.eval_total:,.0f}")
    typer.echo(f"평가손익: {summary.pnl_total:+,.0f}")
    if not summary.holdings:
        typer.echo("(보유 종목 없음)")
        return
    typer.echo("\n보유 종목:")
    for h in summary.holdings:
        typer.echo(
            f"  {h.ticker:>8} {h.name:<16} {h.qty:>6}주  "
            f"평단={h.avg_price:>10,.0f}  현재={h.current_price:>10,.0f}  "
            f"평가={h.eval_amt:>14,.0f}  손익={h.pnl:+,.0f} ({h.pnl_pct:+.2f}%)"
        )


if __name__ == "__main__":
    app()
