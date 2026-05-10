"""해외주식 시세 — KIS Open API 표준 거래소 코드:

- NAS  Nasdaq
- NYS  NYSE
- AMS  AMEX
- HKS  Hong Kong
- TSE  Tokyo
- SHS  Shanghai
- SZS  Shenzhen
"""

from __future__ import annotations

import typer

from app.kis.config import KisEnvironment, parse_env
from app.kis.http import KisHttpClient
from app.kis.models import Quote
from app.kis.tr_id_table import get_tr_id


def current_price(
    symbol: str,
    *,
    exchange: str = "NAS",
    env: KisEnvironment = KisEnvironment.MOCK_OVERSEAS,
) -> Quote:
    sym = symbol.strip().upper()
    client = KisHttpClient(env)
    data = client.get(
        "/uapi/overseas-price/v1/quotations/price",
        tr_id=get_tr_id("overseas-quote", env),
        params={
            "AUTH": "",
            "EXCD": exchange.upper(),
            "SYMB": sym,
        },
    )
    out = data.get("output", {}) or {}

    def _f(k: str) -> float:
        try:
            v = out.get(k)
            return float(v) if v not in (None, "") else 0.0
        except (TypeError, ValueError):
            return 0.0

    return Quote(
        ticker=sym,
        price=_f("last"),
        change=_f("diff"),
        change_pct=_f("rate"),
        volume=int(_f("tvol")),
        high=_f("high"),
        low=_f("low"),
        open=_f("open"),
        prev_close=_f("base"),
        raw=out,
    )


app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def price(
    symbol: str = typer.Option(..., "--symbol", help="예: NVDA, AAPL"),
    exchange: str = typer.Option("NAS", "--exchange"),
    env: str = typer.Option("mock_overseas", "--env"),
) -> None:
    e = parse_env(env)
    q = current_price(symbol, exchange=exchange, env=e)
    typer.echo(f"{q.ticker}@{exchange}  ${q.price:,.2f}  Δ{q.change:+.2f} ({q.change_pct:+.2f}%)")


if __name__ == "__main__":
    app()
