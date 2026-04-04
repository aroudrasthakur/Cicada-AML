-- Per-transaction explanations for fired heuristics (id -> text), for audit and UI.
ALTER TABLE public.run_scores
  ADD COLUMN IF NOT EXISTS heuristic_explanations JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN public.run_scores.heuristic_explanations IS
  'Map of heuristic id (string) to explanation text for each fired heuristic on this transaction.';
