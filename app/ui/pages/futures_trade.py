"""국내 선물옵션 (모의 전용) 거래 페이지."""

from __future__ import annotations

import streamlit as st

from app.kis.config import KisEnvironment
from app.kis.exceptions import KisError
from app.kis.futures import buy as fut_buy, current_price as fut_price, sell as fut_sell
from app.ui.components import env_badge, render_order_form, render_quote_panel


def render() -> None:
    env = KisEnvironment.MOCK_FUTURES
    st.header(f"{env_badge(env)} · 선물옵션 (모의 전용)")
    st.info("선물옵션은 본 앱에서 모의 거래만 지원합니다 — 실전 키는 보관하지 않습니다.")

    code = st.text_input("선물·옵션 코드 (예: 101W3000 KOSPI200 선물)", value="101W3000")

    if code.strip():
        try:
            q = fut_price(code.strip(), env=env)
            render_quote_panel(q)
        except KisError as exc:
            st.error(f"시세 조회 오류: {exc}")

    st.subheader("주문")

    def _buy(ticker: str, qty: int, price: float | None, is_market: bool):
        if price is None:
            st.error("선물옵션 주문은 가격 입력 필수")
            raise KisError("price required")
        return fut_buy(ticker, qty, price, env=env)

    def _sell(ticker: str, qty: int, price: float | None, is_market: bool):
        if price is None:
            st.error("선물옵션 주문은 가격 입력 필수")
            raise KisError("price required")
        return fut_sell(ticker, qty, price, env=env)

    render_order_form(
        env=env, default_ticker=code.strip(),
        on_buy=_buy, on_sell=_sell, is_futures=True,
    )
