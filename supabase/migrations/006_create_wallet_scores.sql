CREATE TABLE public.wallet_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_address TEXT UNIQUE REFERENCES public.wallets (wallet_address),
  risk_score FLOAT,
  fan_in_score FLOAT,
  fan_out_score FLOAT,
  velocity_score FLOAT,
  exposure_score FLOAT,
  scored_at TIMESTAMPTZ DEFAULT now()
);
