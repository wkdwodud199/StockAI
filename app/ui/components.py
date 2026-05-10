"""Streamlit 공통 UI 컴포넌트."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from app.kis.config import KisEnvironment
from app.kis.exceptions import KisError, KisOrderRejected
from app.kis.models import BalanceSummary, Quote


def env_badge(env: KisEnvironment) -> str:
    return ("🟢 모의" if env.is_mock else "🔴 실전") + (
        " · 해외" if env.is_overseas else " · 선물옵션" if env.is_futures else " · 국내"
    )


def _fmt_price(v, sym: str = "") -> str:
    """None / 0 / NaN 안전 포맷."""
    if v is None:
        return "—"
    try:
        return f"{sym}{float(v):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_int(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return "—"


def render_quote_panel(q: Quote, currency: str = "KRW") -> None:
    sym = "₩" if currency == "KRW" else "$"
    try:
        delta = f"{float(q.change):+,.0f} ({float(q.change_pct):+.2f}%)"
    except (TypeError, ValueError):
        delta = ""
    cols = st.columns(4)
    cols[0].metric("현재가", _fmt_price(q.price, sym), delta)
    cols[1].metric("거래량", _fmt_int(q.volume))
    cols[2].metric("고가", _fmt_price(q.high, sym))
    cols[3].metric("저가", _fmt_price(q.low, sym))


def render_orderbook(bids, asks) -> None:
    if not bids and not asks:
        st.info("호가 데이터 없음 (장외 시간일 수 있음)")
        return
    rows = []
    for i in range(max(len(bids), len(asks))):
        b = bids[i] if i < len(bids) else None
        a = asks[i] if i < len(asks) else None
        rows.append(
            {
                "매도잔량": a.qty if a else "",
                "매도호가": f"{a.price:,.0f}" if a else "",
                "매수호가": f"{b.price:,.0f}" if b else "",
                "매수잔량": b.qty if b else "",
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def render_balance(summary: BalanceSummary, currency: str = "KRW") -> None:
    sym = "₩" if currency == "KRW" else "$"
    cols = st.columns(3)
    cols[0].metric("예수금", f"{sym}{summary.deposit:,.0f}")
    cols[1].metric("평가총액", f"{sym}{summary.eval_total:,.0f}")
    cols[2].metric("평가손익", f"{sym}{summary.pnl_total:+,.0f}")
    if not summary.holdings:
        st.caption("보유 종목 없음")
        return
    st.subheader("보유 종목")
    df = pd.DataFrame(
        [
            {
                "종목": f"{h.ticker} {h.name}",
                "수량": h.qty,
                "평단": f"{sym}{h.avg_price:,.0f}",
                "현재가": f"{sym}{h.current_price:,.0f}",
                "평가금액": f"{sym}{h.eval_amt:,.0f}",
                "손익": f"{h.pnl:+,.0f}",
                "수익률": f"{h.pnl_pct:+.2f}%",
            }
            for h in summary.holdings
        ]
    )
    st.dataframe(df, hide_index=True, use_container_width=True)


def render_chart(candles, currency: str = "KRW") -> None:
    if not candles:
        st.info("차트 데이터 없음")
        return
    df = pd.DataFrame(
        [{"date": c.date, "Close": c.close, "Volume": c.volume} for c in candles]
    )
    df = df.set_index("date")
    st.line_chart(df["Close"])


def render_real_mode_gate() -> bool:
    """실전 모드 진입 시 PIN 게이트. True면 잠금 해제 상태."""
    import os

    pin = os.getenv("REAL_MODE_PIN", "0000")
    if st.session_state.get("real_mode_unlocked", False):
        return True
    st.error(
        "🔴 **실전 거래 모드** — 실제 자금이 사용됩니다. "
        "잘못된 주문은 즉시 체결되며 되돌릴 수 없습니다."
    )
    confirmed = st.checkbox("위 사실을 이해했고, 실거래를 진행할 의사가 있습니다.")
    entered_pin = st.text_input("4자리 PIN 입력", type="password", max_chars=4)
    if st.button("잠금 해제", type="primary", disabled=not confirmed):
        if entered_pin == pin:
            st.session_state["real_mode_unlocked"] = True
            st.rerun()
        else:
            st.error("PIN 불일치")
    return False


def render_order_form(
    *,
    env: KisEnvironment,
    default_ticker: str = "",
    on_buy,
    on_sell,
    is_overseas: bool = False,
    is_futures: bool = False,
) -> None:
    """주문 폼.

    실전: form 내부에 '실거래 확인' 체크박스를 포함시켜 한 번의 submit 으로 가드 + 주문 실행.
    모의: 추가 확인 없이 즉시 실행.
    """
    label_ticker = "심볼 (예: NVDA, AAPL)" if is_overseas else (
        "선물코드 (예: 101W3000)" if is_futures else "종목코드 (6자리, 예: 005930)"
    )
    is_real = env.is_real
    with st.form(f"order_form_{env.value}", clear_on_submit=False):
        ticker = st.text_input(label_ticker, value=default_ticker)
        c1, c2, c3 = st.columns([1, 1, 1])
        qty = c1.number_input("수량", min_value=1, value=1, step=1)
        order_type = c2.selectbox("주문 유형", ["지정가", "시장가"])
        price = c3.number_input(
            "가격" + (" (USD)" if is_overseas else ""),
            min_value=0.0,
            value=0.0,
            step=100.0 if not is_overseas else 0.01,
        )

        # 실전 확인 체크박스 — form 내부에 두어 submit 시 함께 검증 (rerun 끊김 회피)
        real_confirm = False
        if is_real:
            real_confirm = st.checkbox(
                "⚠️ 위 내용을 확인했고, 실거래로 즉시 체결합니다.",
                key=f"real_confirm_{env.value}",
            )

        b1, b2 = st.columns(2)
        buy_label = "🔴 매수 실행" if is_real else "🟢 매수"
        sell_label = "🔴 매도 실행" if is_real else "🟢 매도"
        submit_buy = b1.form_submit_button(buy_label, type="primary" if is_real else "secondary")
        submit_sell = b2.form_submit_button(sell_label, type="primary" if is_real else "secondary")

    # form 외부에서 submit 결과 처리
    if submit_buy:
        _execute_order(
            on_buy, ticker, int(qty), price, order_type,
            is_real=is_real, real_confirmed=real_confirm, side="매수",
        )
    if submit_sell:
        _execute_order(
            on_sell, ticker, int(qty), price, order_type,
            is_real=is_real, real_confirmed=real_confirm, side="매도",
        )


def _execute_order(
    fn, ticker: str, qty: int, price: float, order_type: str,
    *, is_real: bool, real_confirmed: bool, side: str,
) -> None:
    if not ticker.strip():
        st.error("종목코드를 입력하세요")
        return
    if is_real and not real_confirmed:
        st.error("실거래 확인 체크박스를 켜고 다시 제출하세요")
        return
    is_market = order_type == "시장가"
    try:
        result = fn(
            ticker=ticker.strip(),
            qty=qty,
            price=None if is_market else float(price),
            is_market=is_market,
        )
    except KisOrderRejected as exc:
        st.error(f"주문 거부 [{exc.msg_cd}] {exc.msg}")
        return
    except KisError as exc:
        st.error(f"오류: {exc}")
        return
    if result.success and result.order_no:
        st.success(f"{side} 주문 완료 — 주문번호 {result.order_no}")
    else:
        st.warning(f"주문 응답: {result.msg or '확인 필요'}")


def auto_refresh_toggle(*, key: str, default_interval: int = 5) -> int:
    """자동 새로고침 토글. 켜진 경우 interval(초) 마다 페이지 rerun.

    반환값: 사용자가 선택한 interval (초). 끄면 0.
    """
    cols = st.columns([1, 2, 4])
    enabled = cols[0].toggle("자동 갱신", value=False, key=f"{key}_toggle")
    interval = cols[1].selectbox(
        "갱신 주기",
        [3, 5, 10, 30],
        index=1,
        format_func=lambda x: f"{x}초",
        key=f"{key}_interval",
        disabled=not enabled,
    )
    if enabled:
        st_autorefresh(interval=interval * 1000, key=f"{key}_autorefresh")
        cols[2].caption(f"⏱ 마지막 갱신: {datetime.now().strftime('%H:%M:%S')}")
        return int(interval)
    return 0


def date_range_inputs(default_days: int = 30) -> tuple[date, date]:
    end = st.date_input("조회 종료일", value=date.today())
    start = st.date_input("조회 시작일", value=end - timedelta(days=default_days))
    if start > end:
        st.error("시작일이 종료일보다 늦습니다")
    return start, end
