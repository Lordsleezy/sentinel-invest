from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import requests


class AlpacaClient:
    def __init__(self) -> None:
        self.key = os.getenv("ALPACA_API_KEY", "")
        self.secret = os.getenv("ALPACA_SECRET_KEY", "")
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets").rstrip("/")
        self.mock_orders: list[dict] = []

    @property
    def configured(self) -> bool:
        return bool(self.key and self.secret)

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.key,
            "APCA-API-SECRET-KEY": self.secret,
            "Content-Type": "application/json",
        }

    def portfolio(self) -> dict:
        if not self.configured:
            return {
                "configured": False,
                "balance": 0,
                "buying_power": 0,
                "positions": [],
                "trade_history": self.mock_orders,
                "message": "ALPACA_API_KEY and ALPACA_SECRET_KEY are not configured; returning local paper state.",
            }
        account = requests.get(f"{self.base_url}/v2/account", headers=self._headers(), timeout=15).json()
        positions = requests.get(f"{self.base_url}/v2/positions", headers=self._headers(), timeout=15).json()
        orders = requests.get(f"{self.base_url}/v2/orders?status=all&limit=50", headers=self._headers(), timeout=15).json()
        return {
            "configured": True,
            "balance": float(account.get("equity", 0)),
            "buying_power": float(account.get("buying_power", 0)),
            "positions": positions,
            "trade_history": orders,
        }

    def submit_bracket_order(self, req) -> dict:
        if not self.configured:
            order = {
                "id": f"mock-{uuid4()}",
                "symbol": req.ticker.upper(),
                "side": req.side.lower(),
                "qty": req.qty,
                "status": "accepted_mock",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "take_profit": req.take_profit,
                "stop_loss": req.stop_loss,
            }
            self.mock_orders.append(order)
            return order

        payload = {
            "symbol": req.ticker.upper(),
            "qty": str(req.qty),
            "side": req.side.lower(),
            "type": "limit",
            "limit_price": str(round(req.entry_price, 2)),
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit": {"limit_price": str(round(req.take_profit, 2))},
            "stop_loss": {"stop_price": str(round(req.stop_loss, 2))},
        }
        resp = requests.post(f"{self.base_url}/v2/orders", headers=self._headers(), json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json()
