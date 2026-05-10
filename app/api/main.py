"""FastAPI 백엔드 — Flutter 모바일 앱이 호출하는 KIS REST 게이트웨이.

⚠️ 보안:
- 모든 엔드포인트는 X-API-Token 헤더 (=환경변수 MOBILE_API_TOKEN) 필수.
- 실전 주문(/order/buy, /order/sell)은 추가 PIN(X-Real-PIN) 필수.
- TradingAgents 분석은 LLM 토큰 비용이 큼 — 폰에서 무분별 호출 차단을 위해
  쿨다운 (메모리 캐시) 적용.
"""

from __future__ import annotations

import os
import time
from datetime import date as _date, timedelta
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.kis.account import inquire_balance, inquire_balance_domestic, inquire_balance_overseas
from app.kis.config import KisEnvironment, parse_env
from app.kis.exceptions import KisError, KisOrderRejected
from app.kis.futures import current_price as futures_price
from app.kis.order_domestic import buy as kis_buy_dom, cancel as kis_cancel, sell as kis_sell_dom
from app.kis.order_overseas import buy as kis_buy_ovs, sell as kis_sell_ovs
from app.kis.quote_domestic import current_price, daily_candles, orderbook
from app.kis.quote_overseas import current_price as overseas_price

load_dotenv()

API_TOKEN = os.getenv("MOBILE_API_TOKEN", "").strip()
REAL_PIN = os.getenv("REAL_MODE_PIN", "0000").strip()

app = FastAPI(
    title="Stock_MTS_TA Mobile API",
    description="KIS Open API 게이트웨이 (Flutter 앱 전용)",
    version="0.1.0",
)


# ---------- 인증 ----------
def require_api_token(x_api_token: Annotated[str, Header()] = "") -> None:
    if not API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MOBILE_API_TOKEN not configured on server",
        )
    if not x_api_token or x_api_token != API_TOKEN:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid X-API-Token")


def require_real_pin(x_real_pin: Annotated[str, Header()] = "") -> None:
    if not x_real_pin or x_real_pin != REAL_PIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "실전 거래 PIN 불일치")


# ---------- 응답 모델 ----------
class QuoteOut(BaseModel):
    ticker: str
    price: float
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    high: float | None = None
    low: float | None = None
    open: float | None = None
    prev_close: float | None = None


class OrderBookLevelOut(BaseModel):
    price: float
    qty: int


class OrderBookOut(BaseModel):
    ticker: str
    bids: list[OrderBookLevelOut]
    asks: list[OrderBookLevelOut]


class CandleOut(BaseModel):
    date: _date
    open: float
    high: float
    low: float
    close: float
    volume: int


class HoldingOut(BaseModel):
    ticker: str
    name: str = ""
    qty: int
    avg_price: float
    current_price: float = 0.0
    eval_amt: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0


class BalanceOut(BaseModel):
    deposit: float = 0.0
    eval_total: float = 0.0
    pnl_total: float = 0.0
    holdings: list[HoldingOut] = Field(default_factory=list)


class OrderResultOut(BaseModel):
    success: bool
    order_no: str | None = None
    msg_cd: str = ""
    msg: str = ""


class OrderRequest(BaseModel):
    env: Literal["mock_domestic", "real_domestic", "mock_overseas", "real_overseas"]
    ticker: str
    qty: int = Field(gt=0)
    price: float | None = None  # None → 시장가 (국내 한정)
    order_type: Literal["limit", "market"] = "limit"
    exchange: str | None = "NAS"  # 해외만 사용


class AnalysisRequest(BaseModel):
    ticker: str
    trade_date: _date


class AnalysisResultOut(BaseModel):
    ticker: str
    trade_date: str
    signal: str
    final_decision: str
    market_report: str = ""
    news_report: str = ""
    fundamentals_report: str = ""
    sentiment_report: str = ""
    investment_plan: str = ""
    trader_plan: str = ""


# ---------- 헬퍼 ----------
def _q_to_out(q) -> QuoteOut:
    return QuoteOut(
        ticker=q.ticker, price=q.price, change=q.change, change_pct=q.change_pct,
        volume=q.volume, high=q.high, low=q.low, open=q.open, prev_close=q.prev_close,
    )


def _result_to_out(r) -> OrderResultOut:
    return OrderResultOut(
        success=r.success, order_no=r.order_no, msg_cd=r.msg_cd, msg=r.msg,
    )


def _balance_to_out(b) -> BalanceOut:
    return BalanceOut(
        deposit=b.deposit, eval_total=b.eval_total, pnl_total=b.pnl_total,
        holdings=[
            HoldingOut(
                ticker=h.ticker, name=h.name, qty=h.qty, avg_price=h.avg_price,
                current_price=h.current_price, eval_amt=h.eval_amt,
                pnl=h.pnl, pnl_pct=h.pnl_pct,
            )
            for h in b.holdings
        ],
    )


# ---------- 엔드포인트 ----------
@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "ts": time.time()}


@app.get("/quote/domestic/{ticker}", response_model=QuoteOut, dependencies=[Depends(require_api_token)])
def quote_domestic(ticker: str, env: str = "mock_domestic") -> QuoteOut:
    e = parse_env(env)
    try:
        return _q_to_out(current_price(ticker, env=e))
    except KisError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


@app.get("/quote/overseas/{symbol}", response_model=QuoteOut, dependencies=[Depends(require_api_token)])
def quote_overseas(symbol: str, exchange: str = "NAS", env: str = "mock_overseas") -> QuoteOut:
    e = parse_env(env)
    try:
        return _q_to_out(overseas_price(symbol, exchange=exchange, env=e))
    except KisError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


@app.get("/orderbook/domestic/{ticker}", response_model=OrderBookOut, dependencies=[Depends(require_api_token)])
def get_orderbook(ticker: str, env: str = "mock_domestic") -> OrderBookOut:
    e = parse_env(env)
    try:
        ob = orderbook(ticker, env=e)
        return OrderBookOut(
            ticker=ob.ticker,
            bids=[OrderBookLevelOut(price=lv.price, qty=lv.qty) for lv in ob.bids],
            asks=[OrderBookLevelOut(price=lv.price, qty=lv.qty) for lv in ob.asks],
        )
    except KisError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


@app.get("/candles/domestic/{ticker}", response_model=list[CandleOut], dependencies=[Depends(require_api_token)])
def get_candles(ticker: str, days: int = 30, env: str = "mock_domestic") -> list[CandleOut]:
    e = parse_env(env)
    end = _date.today()
    start = end - timedelta(days=days)
    try:
        candles = daily_candles(ticker, start, end, env=e)
        return [
            CandleOut(date=c.date, open=c.open, high=c.high, low=c.low, close=c.close, volume=c.volume)
            for c in candles
        ]
    except KisError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


@app.get("/balance", response_model=BalanceOut, dependencies=[Depends(require_api_token)])
def get_balance(env: str = "mock_domestic") -> BalanceOut:
    e = parse_env(env)
    try:
        return _balance_to_out(inquire_balance(e))
    except KisError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


@app.get("/futures/quote/{code}", response_model=QuoteOut, dependencies=[Depends(require_api_token)])
def get_futures_quote(code: str) -> QuoteOut:
    try:
        return _q_to_out(futures_price(code))
    except KisError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


# ---------- 주문 (실전은 PIN 추가 필수) ----------
def _is_real_env(env: KisEnvironment) -> bool:
    return env.is_real


@app.post("/order/buy", response_model=OrderResultOut, dependencies=[Depends(require_api_token)])
def order_buy(
    req: OrderRequest,
    x_real_pin: Annotated[str, Header()] = "",
) -> OrderResultOut:
    e = parse_env(req.env)
    if e.is_real:
        require_real_pin(x_real_pin)
    try:
        if e.is_overseas:
            if req.price is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "해외 주문은 가격 필수")
            r = kis_buy_ovs(req.ticker, req.qty, req.price, exchange=req.exchange or "NAS", env=e)
        else:
            r = kis_buy_dom(
                req.ticker, req.qty, req.price,
                order_type="market" if req.price is None else req.order_type,
                env=e,
            )
        return _result_to_out(r)
    except KisOrderRejected as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"[{exc.msg_cd}] {exc.msg}")
    except KisError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


@app.post("/order/sell", response_model=OrderResultOut, dependencies=[Depends(require_api_token)])
def order_sell(
    req: OrderRequest,
    x_real_pin: Annotated[str, Header()] = "",
) -> OrderResultOut:
    e = parse_env(req.env)
    if e.is_real:
        require_real_pin(x_real_pin)
    try:
        if e.is_overseas:
            if req.price is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "해외 주문은 가격 필수")
            r = kis_sell_ovs(req.ticker, req.qty, req.price, exchange=req.exchange or "NAS", env=e)
        else:
            r = kis_sell_dom(
                req.ticker, req.qty, req.price,
                order_type="market" if req.price is None else req.order_type,
                env=e,
            )
        return _result_to_out(r)
    except KisOrderRejected as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"[{exc.msg_cd}] {exc.msg}")
    except KisError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


# ---------- AI 분석 (쿨다운) ----------
_ANALYSIS_CACHE: dict[tuple[str, str], tuple[float, AnalysisResultOut]] = {}
_ANALYSIS_TTL_SEC = 60 * 60  # 같은 종목·날짜 1시간 내 재호출 차단 (LLM 비용 보호)


@app.post("/analysis", response_model=AnalysisResultOut, dependencies=[Depends(require_api_token)])
def run_ai_analysis(req: AnalysisRequest) -> AnalysisResultOut:
    key = (req.ticker.strip().upper(), req.trade_date.isoformat())
    now = time.time()
    cached = _ANALYSIS_CACHE.get(key)
    if cached and now - cached[0] < _ANALYSIS_TTL_SEC:
        return cached[1]

    from app.integrations.ta_runner import run_analysis  # lazy import (LLM 비용 큼)

    try:
        d = run_analysis(req.ticker, req.trade_date.isoformat())
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"analysis failed: {exc}")

    out = AnalysisResultOut(
        ticker=str(d.get("ticker", req.ticker)),
        trade_date=str(d.get("trade_date", req.trade_date.isoformat())),
        signal=str(d.get("signal", "")),
        final_decision=str(d.get("final_decision", "")),
        market_report=str(d.get("market_report", "")),
        news_report=str(d.get("news_report", "")),
        fundamentals_report=str(d.get("fundamentals_report", "")),
        sentiment_report=str(d.get("sentiment_report", "")),
        investment_plan=str(d.get("investment_plan", "")),
        trader_plan=str(d.get("trader_plan", "")),
    )
    _ANALYSIS_CACHE[key] = (now, out)
    return out
