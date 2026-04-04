CREATE TABLE public.model_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_name TEXT,
  cohort_key TEXT,
  metric_name TEXT,
  metric_value FLOAT,
  window_start TIMESTAMPTZ,
  window_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);
