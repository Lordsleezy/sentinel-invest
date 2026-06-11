from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yfinance as yf

POSITIVE = {"beat", "surge", "record", "upgrade", "growth", "profit", "bull", "strong", "wins", "launch"}
NEGATIVE = {"miss", "drop", "downgrade", "loss", "bear", "weak", "lawsuit", "probe", "cuts", "recall"}


def sentiment_for(text: str) -> str:
    lower = text.lower()
    score = sum(word in lower for word in POSITIVE) - sum(word in lower for word in NEGATIVE)
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"


def latest_news(ticker: str, limit: int = 5) -> list[dict[str, Any]]:
    try:
        raw = yf.Ticker(ticker).news or []
    except Exception:
        raw = []
    items: list[dict[str, Any]] = []
    for item in raw[:limit]:
        content = item.get("content", item)
        title = content.get("title") or item.get("title") or ""
        provider = content.get("provider", {}) if isinstance(content.get("provider"), dict) else {}
        ts = content.get("pubDate") or item.get("providerPublishTime") or ""
        if isinstance(ts, (int, float)):
            ts = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        items.append(
            {
                "title": title,
                "source": provider.get("displayName") or item.get("publisher") or "",
                "url": content.get("canonicalUrl", {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else item.get("link", ""),
                "published_at": str(ts),
                "sentiment": sentiment_for(title),
            }
        )
    return items
