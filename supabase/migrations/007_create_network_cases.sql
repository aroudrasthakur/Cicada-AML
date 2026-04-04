CREATE TABLE public.network_cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_name TEXT,
  typology TEXT,
  risk_score FLOAT,
  total_amount NUMERIC,
  start_time TIMESTAMPTZ,
  end_time TIMESTAMPTZ,
  explanation TEXT,
  graph_snapshot_path TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.network_case_wallets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES public.network_cases (id) ON DELETE CASCADE,
  wallet_address TEXT NOT NULL
);
