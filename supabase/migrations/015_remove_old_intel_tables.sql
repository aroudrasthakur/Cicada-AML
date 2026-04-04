-- Cleanup for DBs that still have removed intel tables/columns from older migration history.
ALTER TABLE public.transaction_scores DROP COLUMN IF EXISTS document_score;
DROP TABLE IF EXISTS public.document_events;
