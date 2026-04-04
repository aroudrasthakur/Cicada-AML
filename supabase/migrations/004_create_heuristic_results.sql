CREATE TABLE public.heuristic_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaction_id TEXT UNIQUE REFERENCES public.transactions (transaction_id),
  heuristic_vector JSONB NOT NULL DEFAULT '[]',
  applicability_vector JSONB NOT NULL DEFAULT '[]',
  triggered_ids JSONB NOT NULL DEFAULT '[]',
  triggered_count INT DEFAULT 0,
  top_typology TEXT,
  top_confidence FLOAT,
  explanations JSONB DEFAULT '{}',
  scored_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_heuristic_results_triggered_count ON public.heuristic_results (triggered_count);
CREATE INDEX idx_heuristic_results_top_typology ON public.heuristic_results (top_typology);
