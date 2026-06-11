# Sentinel Invest

FastAPI backend for Sentinel Prime market signals, watchlists, paper portfolio data, and Alpaca bracket orders.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

The API listens on port `8003`.

## Environment

`ALPACA_API_KEY` and `ALPACA_SECRET_KEY` are optional for read-only endpoints. Without them, `/trade` returns a local mock paper order and `/portfolio` returns local mock state. Add Alpaca paper keys for real paper-account execution.

## Supabase

Run `supabase/schema.sql` in the Sentinel Prime Supabase project to create `invest_trades` before expecting `/trade` rows to persist.
