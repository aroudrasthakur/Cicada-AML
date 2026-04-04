CREATE TABLE public.wallets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_address TEXT UNIQUE NOT NULL,
  chain_id TEXT,
  first_seen TIMESTAMPTZ,
  last_seen TIMESTAMPTZ,
  total_in NUMERIC DEFAULT 0,
  total_out NUMERIC DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_wallets_wallet_address ON public.wallets (wallet_address);
