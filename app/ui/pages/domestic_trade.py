"""국내주식 거래 페이지 (실전·모의 공용 — env로 분기)."""

from __future__ import annotations

import streamlit as st

from app.kis.account import inquire_balance_domestic
from app.kis.config import KisEnvironment
from app.kis.exceptions import KisError
from app.kis.order_domestic import buy as kis_buy, sell as kis_sell
from app.kis.quote_domestic import current_price, daily_candles, orderbook
from app.ui.components import (
    auto_refresh_toggle,
    date_range_inputs,
    env_badge,
    render_balance,
    render_chart,
    render_order_form,
    render_orderbook,
    render_quote_panel,
    render_real_mode_gate,
)


def render(env: KisEnvironment) -> None:
    st.header(f"{env_badge(env)} · 국내주식")

    if env.is_real and not render_real_mode_gate():
        return

    if env.is_real:
        st.warning("🔴 실전 모드 잠금 해제 상태 — 모든 매매는 실제 자금으로 즉시 체결됩니다.")

    tab_quote, tab_chart, tab_balance = st.tabs(["📊 시세 / 주문", "📈 차트", "💰 잔고"])

    with tab_quote:
        ticker = st.text_input("종목코드 (6자리)", value=st.session_state.get("ai_picked_ticker", "005930"))
        auto_refresh_toggle(key=f"quote_{env.value}")
        if ticker.strip():
            try:
                q = current_price(ticker.strip(), env=env)
                render_quote_panel(q)
                ob = orderbook(ticker.strip(), env=env)
                st.subheader("호가창 (10단)")
                render_orderbook(ob.bids, ob.asks)
            except KisError as exc:
                st.error(f"시세 조회 오류: {exc}")

        st.subheader("주문")

        def _buy(ticker: str, qty: int, price: float | None, is_market: bool):
            return kis_buy(
                ticker, qty, price,
                order_type="market" if is_market else "limit",
                env=env,
            )

        def _sell(ticker: str, qty: int, price: float | None, is_market: bool):
            return kis_sell(
                ticker, qty, price,
                order_type="market" if is_market else "limit",
                env=env,
            )

        render_order_form(env=env, default_ticker=ticker.strip(), on_buy=_buy, on_sell=_sell)

    with tab_chart:
        ticker = st.text_input("종목코드", value="005930", key=f"chart_ticker_{env.value}")
        start, end = date_range_inputs(60)
        if ticker.strip() and start <= end:
            try:
                candles = daily_candles(ticker.strip(), start, end, env=env)
                render_chart(candles)
                st.caption(f"{len(candles)}개 캔들")
            except KisError as exc:
                st.error(f"차트 조회 오류: {exc}")

    with tab_balance:
        try:
            summary = inquire_balance_domestic(env=env)
            render_balance(summary)
        except KisError as exc:
            st.error(f"잔고 조회 오류: {exc}")
