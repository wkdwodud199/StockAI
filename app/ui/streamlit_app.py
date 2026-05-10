"""Streamlit 메인 진입점.

실행: `.\\scripts\\run.ps1` 또는 `streamlit run app/ui/streamlit_app.py`
"""

from __future__ import annotations

import streamlit as st

from app.kis.config import KisEnvironment

st.set_page_config(
    page_title="KIS + TradingAgents",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# .env 로드 (KIS credentials, LLM provider 등)
from app.kis.credentials import _ensure_dotenv  # noqa: E402

_ensure_dotenv()

# 사이드바 메뉴
MENU_OPTIONS = [
    ("home", "🏠 홈"),
    ("mock_dom", "🟢 모의투자 · 국내주식"),
    ("mock_ovs", "🟢 모의투자 · 해외주식"),
    ("mock_fut", "🟢 모의투자 · 선물옵션"),
    ("real_dom", "🔴 실전투자 · 국내주식"),
    ("real_ovs", "🔴 실전투자 · 해외주식"),
    ("ai", "🤖 AI 분석 (TradingAgents)"),
]

with st.sidebar:
    st.markdown("# KIS + TA")
    st.caption("한국투자증권 + TradingAgents")
    selection_label = st.radio(
        "메뉴",
        [label for _, label in MENU_OPTIONS],
        label_visibility="collapsed",
    )
    selection_key = next(k for k, label in MENU_OPTIONS if label == selection_label)

    st.divider()
    if st.session_state.get("real_mode_unlocked"):
        st.success("🔓 실전 모드 잠금 해제됨")
        if st.button("🔒 실전 모드 잠그기"):
            st.session_state["real_mode_unlocked"] = False
            st.rerun()
    else:
        st.caption("실전 메뉴는 PIN으로 잠겨 있습니다")


# 라우팅
if selection_key == "home":
    from app.ui.pages.home import render
    render()
elif selection_key == "mock_dom":
    from app.ui.pages.domestic_trade import render
    render(KisEnvironment.MOCK_DOMESTIC)
elif selection_key == "mock_ovs":
    from app.ui.pages.overseas_trade import render
    render(KisEnvironment.MOCK_OVERSEAS)
elif selection_key == "mock_fut":
    from app.ui.pages.futures_trade import render
    render()
elif selection_key == "real_dom":
    from app.ui.pages.domestic_trade import render
    render(KisEnvironment.REAL_DOMESTIC)
elif selection_key == "real_ovs":
    from app.ui.pages.overseas_trade import render
    render(KisEnvironment.REAL_OVERSEAS)
elif selection_key == "ai":
    from app.ui.pages.ai_analysis import render
    render()
