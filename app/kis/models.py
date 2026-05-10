"""KIS API 응답 Pydantic 모델."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class Quote(BaseModel):
    """국내/해외 주식 현재가 표준화."""

    ticker: str
    price: float
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    high: float | None = None
    low: float | None = None
    open: float | None = None
    prev_close: float | None = None
    timestamp: datetime | None = None
    raw: dict = Field(default_factory=dict, repr=False)


class OrderBookLevel(BaseModel):
    price: float
    qty: int


class OrderBook(BaseModel):
    ticker: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    timestamp: datetime | None = None
    raw: dict = Field(default_factory=dict, repr=False)


class Candle(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class OrderResult(BaseModel):
    """주문 응답."""

    success: bool
    order_no: str | None = None
    krx_fwdg_ord_orgno: str | None = None  # 한국거래소전송주문조직번호
    ord_tmd: str | None = None
    msg_cd: str = ""
    msg: str = ""
    raw: dict = Field(default_factory=dict, repr=False)


class Holding(BaseModel):
    ticker: str
    name: str = ""
    qty: int
    avg_price: float
    current_price: float = 0.0
    eval_amt: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0


class BalanceSummary(BaseModel):
    deposit: float = 0.0  # 예수금
    eval_total: float = 0.0  # 평가총액
    pnl_total: float = 0.0  # 평가손익
    holdings: list[Holding] = Field(default_factory=list)


OrderSide = Literal["buy", "sell"]
OrderType = Literal["market", "limit"]
