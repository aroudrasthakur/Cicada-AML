CREATE TABLE public.transaction_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaction_id TEXT UNIQUE REFERENCES public.transactions (transaction_id),
  behavioral_score FLOAT,
  behavioral_anomaly_score FLOAT,
  graph_score FLOAT,
  entity_score FLOAT,
  temporal_score FLOAT,
  document_score FLOAT,
  offramp_score FLOAT,
  meta_score FLOAT,
  predicted_label TEXT,
  explanation_summary TEXT,
  scored_at TIMESTAMPTZ DEFAULT now()
);
