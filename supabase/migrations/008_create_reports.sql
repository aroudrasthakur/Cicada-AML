CREATE TABLE public.reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID REFERENCES public.network_cases (id),
  title TEXT,
  report_path TEXT,
  generated_at TIMESTAMPTZ DEFAULT now()
);
