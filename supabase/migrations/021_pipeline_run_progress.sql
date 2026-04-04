-- Granular pipeline progress for UI (steps, scoring, lens workload).

ALTER TABLE public.pipeline_runs
  ADD COLUMN IF NOT EXISTS current_step TEXT,
  ADD COLUMN IF NOT EXISTS progress_log JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS scoring_tx_done INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS scoring_tx_total INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS lenses_completed INT DEFAULT 0;

COMMENT ON COLUMN public.pipeline_runs.current_step IS 'Human-readable pipeline phase';
COMMENT ON COLUMN public.pipeline_runs.progress_log IS 'Append-only [{t, msg}, ...] capped in app';
COMMENT ON COLUMN public.pipeline_runs.scoring_tx_done IS 'Transactions scored so far (ML phase)';
COMMENT ON COLUMN public.pipeline_runs.scoring_tx_total IS 'Total transactions to score';
COMMENT ON COLUMN public.pipeline_runs.lenses_completed IS '0-5 workload indicator mapped from scoring progress';
