CREATE TABLE public.threshold_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cohort_key TEXT UNIQUE,
  alert_threshold FLOAT,
  case_threshold FLOAT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
