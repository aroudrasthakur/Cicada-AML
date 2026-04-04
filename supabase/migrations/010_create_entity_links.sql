CREATE TABLE public.entity_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_address TEXT,
  entity_id TEXT,
  link_type TEXT,
  link_strength FLOAT,
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
