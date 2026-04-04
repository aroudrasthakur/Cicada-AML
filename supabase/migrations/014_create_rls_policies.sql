-- Enable RLS on all application tables
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.heuristic_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transaction_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wallet_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.network_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.network_case_wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entity_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.address_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.threshold_policies ENABLE ROW LEVEL SECURITY;

-- Authenticated: SELECT + INSERT on all tables
CREATE POLICY "authenticated_select_transactions" ON public.transactions FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_transactions" ON public.transactions FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_wallets" ON public.wallets FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_wallets" ON public.wallets FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_edges" ON public.edges FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_edges" ON public.edges FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_heuristic_results" ON public.heuristic_results FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_heuristic_results" ON public.heuristic_results FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_transaction_scores" ON public.transaction_scores FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_transaction_scores" ON public.transaction_scores FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_wallet_scores" ON public.wallet_scores FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_wallet_scores" ON public.wallet_scores FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_network_cases" ON public.network_cases FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_network_cases" ON public.network_cases FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_network_case_wallets" ON public.network_case_wallets FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_network_case_wallets" ON public.network_case_wallets FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_reports" ON public.reports FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_reports" ON public.reports FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_document_events" ON public.document_events FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_document_events" ON public.document_events FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_entity_links" ON public.entity_links FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_entity_links" ON public.entity_links FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_address_tags" ON public.address_tags FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_address_tags" ON public.address_tags FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_model_metrics" ON public.model_metrics FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_model_metrics" ON public.model_metrics FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "authenticated_select_threshold_policies" ON public.threshold_policies FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_threshold_policies" ON public.threshold_policies FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "authenticated_update_threshold_policies" ON public.threshold_policies FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
