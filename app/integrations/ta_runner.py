"""TradingAgents propagate() 래퍼 — LLM provider 라우팅 + 결과 정규화."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterator

from app.integrations.ta_kis_patch import enable_kis_for_korean_tickers


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    deep_model: str
    quick_model: str
    backend_url: str | None = None


def _resolve_llm_config() -> LLMConfig:
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower().strip()
    if provider == "anthropic":
        return LLMConfig(
            provider="anthropic",
            deep_model=os.getenv("TA_DEEP_LLM", "claude-sonnet-4-5"),
            quick_model=os.getenv("TA_QUICK_LLM", "claude-haiku-4-5-20251001"),
            backend_url=None,
        )
    if provider == "openai":
        return LLMConfig(
            provider="openai",
            deep_model=os.getenv("TA_DEEP_LLM", "gpt-5.2-chat-latest"),
            quick_model=os.getenv("TA_QUICK_LLM", "gpt-5.2-chat-latest"),
            backend_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
    if provider == "ollama":
        return LLMConfig(
            provider="ollama",
            deep_model=os.getenv("TA_DEEP_LLM", "qwen2.5"),
            quick_model=os.getenv("TA_QUICK_LLM", "llama3.2"),
            backend_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        )
    raise ValueError(
        f"unknown LLM_PROVIDER={provider!r}. supported: anthropic, openai, ollama"
    )


def _make_config() -> dict[str, Any]:
    from tradingagents.default_config import DEFAULT_CONFIG

    cfg = DEFAULT_CONFIG.copy()
    llm = _resolve_llm_config()
    cfg["llm_provider"] = llm.provider
    cfg["deep_think_llm"] = llm.deep_model
    cfg["quick_think_llm"] = llm.quick_model
    if llm.backend_url:
        cfg["backend_url"] = llm.backend_url
    return cfg


def _normalize_result(final_state: dict, signal: Any) -> dict:
    """propagate 결과를 UI에서 다루기 쉬운 dict로 압축."""
    return {
        "ticker": final_state.get("company_of_interest"),
        "trade_date": final_state.get("trade_date"),
        "signal": str(signal) if signal is not None else "",
        "final_decision": final_state.get("final_trade_decision", ""),
        "investment_plan": final_state.get("investment_plan", ""),
        "trader_plan": final_state.get("trader_investment_plan", ""),
        "market_report": final_state.get("market_report", ""),
        "news_report": final_state.get("news_report", ""),
        "fundamentals_report": final_state.get("fundamentals_report", ""),
        "sentiment_report": final_state.get("sentiment_report", ""),
        "raw_state": final_state,
    }


def run_analysis(ticker: str, trade_date: str, *, debug: bool = False) -> dict:
    """주어진 종목/날짜에 대해 TradingAgents 파이프라인 실행."""
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    enable_kis_for_korean_tickers()
    cfg = _make_config()
    graph = TradingAgentsGraph(debug=debug, config=cfg)
    final_state, signal = graph.propagate(ticker, trade_date)
    return _normalize_result(final_state, signal)


def run_analysis_streaming(
    ticker: str, trade_date: str
) -> Iterator[dict]:
    """Streamlit `st.write_stream`용 — chunk 단위로 yield (debug 트레이싱 활용).

    각 chunk는 `{"event": "message", "agent": ..., "content": ...}` 형태.
    완료 시 `{"event": "done", "result": <run_analysis dict>}` 1회.
    """
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    enable_kis_for_korean_tickers()
    cfg = _make_config()
    graph = TradingAgentsGraph(debug=False, config=cfg)
    init_state = graph.propagator.create_initial_state(ticker, trade_date)
    args = graph.propagator.get_graph_args()

    final_chunk: dict = {}
    for chunk in graph.graph.stream(init_state, **args):
        msgs = chunk.get("messages", [])
        if msgs:
            last = msgs[-1]
            yield {
                "event": "message",
                "content": getattr(last, "content", str(last)),
            }
        final_chunk = chunk

    final_state = final_chunk
    signal = graph.process_signal(final_state.get("final_trade_decision", ""))
    yield {"event": "done", "result": _normalize_result(final_state, signal)}
