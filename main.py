from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
import requests

from alpaca_client import AlpacaClient
from models import TradeRequest
from news import latest_news
from scanner import jobs, market_pulse, scan_market, start_scan_job, watchlist
from scheduler import start_scheduler, stop_scheduler

load_dotenv()
alpaca = AlpacaClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Sentinel Invest", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/signals")
def signals():
    return scan_market(limit=10)


@app.get("/watchlist")
def get_watchlist():
    return watchlist()


@app.get("/portfolio")
def portfolio():
    return alpaca.portfolio()


@app.post("/trade")
def trade(req: TradeRequest):
    try:
        order = alpaca.submit_bracket_order(req)
    except Exception as exc:
        raise HTTPException(502, f"Alpaca order failed: {exc}") from exc
    _log_trade(req, order)
    return {"order_id": order.get("id"), "status": order.get("status", "submitted"), "details": order}


@app.get("/news/{ticker}")
def news(ticker: str):
    return latest_news(ticker, limit=5)


@app.post("/scan")
def scan(background_tasks: BackgroundTasks):
    job_id = start_scan_job()
    return {"job_id": job_id}


@app.get("/scan/{job_id}")
def scan_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "scan job not found")
    return jobs[job_id]


@app.get("/market-pulse")
def pulse():
    return market_pulse()


def _log_trade(req: TradeRequest, order: dict) -> None:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return
    try:
        requests.post(
            f"{url.rstrip('/')}/rest/v1/invest_trades",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json={
                "ticker": req.ticker.upper(),
                "side": req.side.lower(),
                "qty": req.qty,
                "entry_price": req.entry_price,
                "take_profit": req.take_profit,
                "stop_loss": req.stop_loss,
                "order_id": order.get("id"),
                "status": order.get("status"),
                "details": order,
            },
            timeout=10,
        )
    except Exception:
        return


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8003")))
