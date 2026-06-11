from __future__ import annotations

import concurrent.futures
import time
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
import requests
import yfinance as yf

from news import latest_news
from signals import bollinger, macd, rsi

DEFAULT_WATCHLIST = ["NVDA", "AAPL", "TSLA", "MSFT", "AMD", "BTC-USD", "ETH-USD", "SPY", "QQQ"]
SCAN_UNIVERSE = [
    "NVDA", "AAPL", "TSLA", "MSFT", "AMD", "META", "AMZN", "GOOGL", "NFLX", "AVGO",
    "PLTR", "SMCI", "MSTR", "COIN", "HOOD", "SOFI", "RIVN", "LCID", "NIO", "BABA",
    "INTC", "MU", "ARM", "ORCL", "CRM", "UBER", "SHOP", "SQ", "PYPL", "JPM",
    "BAC", "XOM", "CVX", "BA", "CAT", "SPY", "QQQ", "IWM", "BTC-USD", "ETH-USD",
]

jobs: dict[str, dict] = {}
latest_signals_cache: list[dict] = []


def _history(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    return yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)


def _col(hist: pd.DataFrame, name: str) -> pd.Series:
    data = hist[name]
    if isinstance(data, pd.DataFrame):
        return data.iloc[:, 0]
    return data


def _last_float(series) -> float:
    value = series.dropna().iloc[-1]
    try:
        return float(value.item())
    except AttributeError:
        return float(value)


def analyze_ticker(ticker: str) -> dict | None:
    try:
        hist = _history(ticker)
        if hist.empty or len(hist) < 50:
            return None
        close = _col(hist, "Close")
        volume = _col(hist, "Volume")
        price = _last_float(close)
        rsi_value = rsi(close)
        macd_line, macd_sig = macd(close)
        upper, lower = bollinger(close)
        ma20 = _last_float(close.rolling(20).mean())
        ma50 = _last_float(close.rolling(50).mean())
        ma200 = _last_float(close.rolling(min(200, len(close))).mean())
        vol_avg = _last_float(volume.rolling(20).mean())
        vol_now = _last_float(volume)
        volume_ratio = float(vol_now / vol_avg) if vol_avg else 1.0

        score = 45.0
        bull: list[str] = []
        bear: list[str] = []
        flags: list[str] = []
        if rsi_value is not None and rsi_value < 35:
            score += 16
            bull.append("RSI is oversold and could mean-revert.")
            flags.append("RSI < 35")
        if rsi_value is not None and rsi_value > 65:
            score += 8
            bear.append("RSI is elevated; momentum may be crowded.")
            flags.append("RSI > 65")
        if volume_ratio > 2:
            score += 14
            bull.append("Volume is more than 2x the 20-day average.")
            flags.append("volume spike")
        if price > ma20 > ma50:
            score += 12
            bull.append("Price is trending above the 20-day and 50-day averages.")
            flags.append("MA trend")
        if price < ma20:
            bear.append("Price is below the 20-day average.")
        if macd_line is not None and macd_sig is not None and macd_line > macd_sig:
            score += 10
            bull.append("MACD is above signal.")
            flags.append("MACD bullish")
        elif macd_line is not None and macd_sig is not None:
            bear.append("MACD is below signal.")

        headlines = latest_news(ticker)
        sentiment_score = sum(1 if n["sentiment"] == "positive" else -1 if n["sentiment"] == "negative" else 0 for n in headlines)
        score += sentiment_score * 4
        score = max(0, min(100, score))

        target = round(price * 1.015, 2)
        stop = round(price * 0.992, 2)
        risk = round(max(price - stop, 0), 2)
        reward = round(max(target - price, 0), 2)
        return {
            "ticker": ticker,
            "direction": "long" if score >= 50 else "watch",
            "confidence": round(score, 1),
            "entry_price": round(price, 2),
            "target_price": target,
            "stop_price": stop,
            "catalyst": ", ".join(flags) or "No major catalyst detected",
            "technical_summary": f"Price {price:.2f}; MA20 {ma20:.2f}; MA50 {ma50:.2f}; MA200 {ma200:.2f}; Bollinger {lower or 0:.2f}-{upper or 0:.2f}",
            "rsi": round(rsi_value, 2) if rsi_value is not None else None,
            "macd_signal": round(macd_sig, 4) if macd_sig is not None else None,
            "volume_ratio": round(volume_ratio, 2),
            "news_headlines": headlines[:5],
            "bull_case": bull[:5] or ["Setup is liquid and actively monitored."],
            "bear_case": bear[:5] or ["No major bearish technical flag detected."],
            "risk_dollars": risk,
            "reward_dollars": reward,
            "rr_ratio": round(reward / risk, 2) if risk else 0,
        }
    except Exception:
        return None


def scan_market(limit: int = 10, max_workers: int = 8) -> list[dict]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        rows = list(pool.map(analyze_ticker, SCAN_UNIVERSE))
    signals = [row for row in rows if row and row.get("entry_price")]
    signals.sort(key=lambda row: row["confidence"], reverse=True)
    global latest_signals_cache
    latest_signals_cache = signals[:limit]
    return latest_signals_cache


def start_scan_job() -> str:
    job_id = str(uuid4())
    jobs[job_id] = {"status": "running", "progress": 0, "candidates_found": 0, "top_signals": []}

    def run() -> None:
        try:
            start = time.time()
            signals = scan_market()
            jobs[job_id].update(
                {
                    "status": "complete",
                    "progress": 100,
                    "candidates_found": len(signals),
                    "top_signals": signals,
                    "duration_seconds": round(time.time() - start, 2),
                }
            )
        except Exception as exc:
            jobs[job_id].update({"status": "failed", "progress": 100, "error": str(exc)})

    concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(run)
    return job_id


def watchlist() -> list[dict]:
    rows = []
    for ticker in DEFAULT_WATCHLIST:
        hist = _history(ticker, period="5d", interval="1h")
        if hist.empty:
            rows.append({"ticker": ticker, "price": None, "change_1d": None, "ai_score": 0, "history": []})
            continue
        close = _col(hist, "Close")
        price = _last_float(close)
        first = _last_float(close.dropna().head(1))
        rows.append(
            {
                "ticker": ticker,
                "price": round(price, 2),
                "change_1d": round(((price - first) / first) * 100, 2) if first else 0,
                "ai_score": analyze_ticker(ticker).get("confidence", 0) if ticker in DEFAULT_WATCHLIST[:5] else 50,
                "history": [{"time": str(idx), "price": round(_last_float(pd.Series([value])), 2)} for idx, value in close.dropna().tail(40).items()],
            }
        )
    return rows


def market_pulse() -> dict:
    try:
        fg = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10).json()["data"][0]
        fear = float(fg["value"])
        label = fg["value_classification"]
    except Exception:
        fear, label = 50.0, "Neutral"
    sectors = {"XLK": "technology", "XLF": "financials", "XLE": "energy", "XLV": "healthcare", "XLY": "consumer_discretionary"}
    perf = {}
    for symbol, sector in sectors.items():
        hist = _history(symbol, period="5d", interval="1d")
        if len(hist) >= 2:
            close = _col(hist, "Close").dropna()
            latest = _last_float(close)
            previous = _last_float(close.iloc[:-1])
            perf[sector] = round((latest - previous) / previous * 100, 2)
    vix_hist = _history("^VIX", period="5d", interval="1d")
    vix = round(_last_float(_col(vix_hist, "Close")), 2) if not vix_hist.empty else None
    return {"fear_greed_index": fear, "fear_greed_label": label, "vix": vix, "sector_performance": perf}


def intraday_scan() -> list[dict]:
    return [s for s in scan_market(limit=20) if s["confidence"] > 75]


def premarket_scan() -> list[dict]:
    return scan_market()


def overnight_analysis() -> list[dict]:
    return scan_market()


def crypto_scan() -> dict:
    try:
        return requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true",
            timeout=10,
        ).json()
    except Exception:
        return {}
