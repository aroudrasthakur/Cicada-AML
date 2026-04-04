CREATE TABLE public.edges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sender_wallet TEXT NOT NULL,
  receiver_wallet TEXT NOT NULL,
  transaction_id TEXT REFERENCES public.transactions (transaction_id),
  amount NUMERIC,
  timestamp TIMESTAMPTZ
);

CREATE INDEX idx_edges_sender_wallet ON public.edges (sender_wallet);
CREATE INDEX idx_edges_receiver_wallet ON public.edges (receiver_wallet);
