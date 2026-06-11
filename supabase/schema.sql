create table if not exists public.invest_trades (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  ticker text not null,
  side text not null,
  qty numeric not null,
  entry_price numeric not null,
  take_profit numeric not null,
  stop_loss numeric not null,
  order_id text,
  status text,
  details jsonb not null default '{}'::jsonb
);

create index if not exists invest_trades_created_at_idx
  on public.invest_trades (created_at desc);

create index if not exists invest_trades_ticker_idx
  on public.invest_trades (ticker);
