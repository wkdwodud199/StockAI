"""해외주식 거래 페이지."""

from __future__ import annotations

import streamlit as st

from app.kis.account import inquire_balance_overseas
from app.kis.config import KisEnvironment
from app.kis.exceptions import KisError
from app.kis.order_overseas import buy as kis_buy, sell as kis_sell
from app.kis.quote_overseas import current_price
from app.ui.components import (
    env_badge,
    render_balance,
    render_order_form,
    render_quote_panel,
    render_real_mode_gate,
)


def render(env: KisEnvironment) -> None:
    st.header(f"{env_badge(env)} · 해외주식")

    if env.is_real and not render_real_mode_gate():
        return

    if env.is_real:
        st.warning("🔴 실전 모드 잠금 해제 상태 — 모든 매매는 실제 자금으로 즉시 체결됩니다.")

    exchange = st.selectbox("거래소", ["NAS", "NYS", "AMS"], help="NAS=NASDAQ, NYS=NYSE, AMS=AMEX")
    symbol = st.text_input("심볼 (예: NVDA, AAPL)", value="NVDA")

    tab_quote, tab_balance = st.tabs(["📊 시세 / 주문", "💰 잔고"])

    with tab_quote:
        if symbol.strip():
            try:
                q = current_price(symbol.strip(), exchange=exchange, env=env)
                render_quote_panel(q, currency="USD")
            except KisError as exc:
                st.error(f"시세 조회 오류: {exc}")

        st.subheader("주문")

        def _buy(ticker: str, qty: int, price: float | None, is_market: bool):
            if price is None:
                st.error("해외주식 주문은 가격 입력 필수 (시장가 미지원)")
                raise KisError("price required for overseas orders")
            return kis_buy(ticker, qty, price, exchange=exchange, env=env)

        def _sell(ticker: str, qty: int, price: float | None, is_market: bool):
            if price is None:
                st.error("해외주식 주문은 가격 입력 필수 (시장가 미지원)")
                raise KisError("price required for overseas orders")
            return kis_sell(ticker, qty, price, exchange=exchange, env=env)

        render_order_form(
            env=env, default_ticker=symbol.strip(),
            on_buy=_buy, on_sell=_sell, is_overseas=True,
        )

    with tab_balance:
        try:
            summary = inquire_balance_overseas(env=env)
            render_balance(summary, currency="USD")
        except KisError as exc:
            st.error(f"잔고 조회 오류: {exc}")
