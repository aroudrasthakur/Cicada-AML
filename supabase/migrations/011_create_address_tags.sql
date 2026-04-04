CREATE TABLE public.address_tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_address TEXT,
  tag TEXT,
  tag_source TEXT,
  confidence FLOAT,
  valid_from TIMESTAMPTZ,
  valid_to TIMESTAMPTZ
);
