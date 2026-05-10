"""TradingAgents AI 분석 페이지."""

from __future__ import annotations

from datetime import date

import streamlit as st


def render() -> None:
    st.header("🤖 AI 분석 — TradingAgents")
    st.caption(
        "다중 에이전트(Analysts → Researchers → Trader → Risk Mgmt → Portfolio Manager) "
        "파이프라인이 종목을 분석합니다. KRX 6자리는 KIS, 그 외는 yfinance로 데이터 수집."
    )

    import os
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    key_var = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "ollama": "OLLAMA_BASE_URL",
    }.get(provider)
    if not os.getenv(key_var or "", "").strip():
        st.error(
            f"⚠️ LLM 키 미설정: {key_var}. .env 파일에 키를 추가하거나 "
            f"환경변수 LLM_PROVIDER 변경 후 재실행하세요."
        )

    c1, c2 = st.columns(2)
    ticker = c1.text_input("종목코드 (예: 005930 또는 NVDA)", value="005930")
    trade_date = c2.date_input("분석 기준일", value=date.today())

    st.warning(
        "💡 1회 분석은 LLM 토큰을 수만~수십만 단위로 사용합니다 "
        "(약 $0.10~$1.00, provider/모델별 차이). 필요 시에만 실행하세요."
    )

    if st.button("▶ 분석 시작", type="primary", disabled=not ticker.strip()):
        from app.integrations.ta_runner import run_analysis_streaming

        log_box = st.container(border=True)
        result_holder: dict = {}

        with st.spinner(f"{ticker.upper()} 분석 중... (수 분 소요)"):
            try:
                for chunk in run_analysis_streaming(ticker.strip(), trade_date.isoformat()):
                    if chunk["event"] == "message":
                        with log_box:
                            content = str(chunk.get("content", ""))[:1500]
                            if content:
                                st.markdown(f"```\n{content}\n```")
                    elif chunk["event"] == "done":
                        result_holder.update(chunk["result"])
            except Exception as exc:  # pragma: no cover
                st.exception(exc)
                return

        if not result_holder:
            st.error("분석 결과를 받지 못함")
            return

        st.success("✅ 분석 완료")
        st.subheader("최종 거래 결정 (Portfolio Manager)")
        st.markdown(result_holder.get("final_decision", "_(없음)_"))

        with st.expander("📊 시장 분석 (Market Report)"):
            st.markdown(result_holder.get("market_report", "_(없음)_"))
        with st.expander("📰 뉴스 분석 (News Report)"):
            st.markdown(result_holder.get("news_report", "_(없음)_"))
        with st.expander("💼 펀더멘털 분석 (Fundamentals Report)"):
            st.markdown(result_holder.get("fundamentals_report", "_(없음)_"))
        with st.expander("💬 센티먼트 분석 (Sentiment Report)"):
            st.markdown(result_holder.get("sentiment_report", "_(없음)_"))
        with st.expander("📋 투자 계획 (Investment Plan)"):
            st.markdown(result_holder.get("investment_plan", "_(없음)_"))
        with st.expander("👤 트레이더 결정 (Trader Plan)"):
            st.markdown(result_holder.get("trader_plan", "_(없음)_"))

        st.divider()
        if st.button("📤 이 종목을 거래 페이지로 보내기"):
            st.session_state["ai_picked_ticker"] = ticker.strip()
            st.success(f"{ticker.upper()}이(가) 거래 폼에 미리 채워졌습니다. 사이드바에서 거래 페이지로 이동하세요.")
