CREATE TABLE public.transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaction_id TEXT UNIQUE,
  tx_hash TEXT,
  sender_wallet TEXT NOT NULL,
  receiver_wallet TEXT NOT NULL,
  amount NUMERIC NOT NULL,
  asset_type TEXT,
  chain_id TEXT,
  timestamp TIMESTAMPTZ NOT NULL,
  fee NUMERIC,
  label TEXT,
  label_source TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_transactions_sender_wallet ON public.transactions (sender_wallet);
CREATE INDEX idx_transactions_receiver_wallet ON public.transactions (receiver_wallet);
CREATE INDEX idx_transactions_timestamp ON public.transactions (timestamp);
CREATE INDEX idx_transactions_label ON public.transactions (label);
