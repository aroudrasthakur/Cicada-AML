CREATE TABLE public.document_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id TEXT,
  transaction_id TEXT,
  doc_type TEXT,
  parsed_fields JSONB,
  quality_score FLOAT,
  created_at TIMESTAMPTZ DEFAULT now()
);
