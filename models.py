from __future__ import annotations

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    title: str
    source: str = ""
    url: str = ""
    published_at: str = ""
    sentiment: str = "neutral"


class Signal(BaseModel):
    ticker: str
    direction: str
    confidence: float
    entry_price: float
    target_price: float
    stop_price: float
    catalyst: str
    technical_summary: str
    rsi: float | None = None
    macd_signal: float | None = None
    volume_ratio: float | None = None
    news_headlines: list[NewsItem] = Field(default_factory=list)
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    risk_dollars: float
    reward_dollars: float
    rr_ratio: float


class TradeRequest(BaseModel):
    ticker: str
    side: str
    qty: float
    entry_price: float
    take_profit: float
    stop_loss: float
