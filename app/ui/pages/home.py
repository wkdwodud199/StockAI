"""홈 — 모의 계좌 요약."""

from __future__ import annotations

import streamlit as st

from app.kis.account import inquire_balance_domestic
from app.kis.config import KisEnvironment
from app.kis.exceptions import KisError
from app.ui.components import render_balance


def render() -> None:
    st.header("🏠 홈")
    st.write(
        "한국투자증권 KIS Open API + TradingAgents 다중 에이전트 분석을 결합한 트레이딩 앱."
    )

    st.markdown(
        """
        **메뉴 안내**
        - 🟢 모의투자 (국내 / 해외 / 선물옵션) — 가짜 자금으로 자유롭게 연습
        - 🔴 실전투자 (국내 / 해외) — 4자리 PIN 잠금 해제 + 매번 확인
        - 🤖 AI 분석 — TradingAgents가 종목 분석 후 매수/매도 추천
        """
    )

    st.divider()
    st.subheader("모의 국내주식 계좌 요약")
    try:
        summary = inquire_balance_domestic(env=KisEnvironment.MOCK_DOMESTIC)
        render_balance(summary)
    except KisError as exc:
        st.error(f"계좌 조회 오류: {exc}")
        st.caption("`.env` 파일의 KIS 자격증명을 확인하세요. 마이그레이션: `.\\scripts\\migrate_secrets.ps1`")
