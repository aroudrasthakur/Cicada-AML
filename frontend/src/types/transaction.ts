export interface Transaction {
  id: string;
  transaction_id: string;
  tx_hash: string | null;
  sender_wallet: string;
  receiver_wallet: string;
  amount: number;
  asset_type: string | null;
  chain_id: string | null;
  timestamp: string;
  fee: number | null;
  label: string | null;
  label_source: string | null;
  created_at: string;
  /** Present when transaction is joined with scoring for tables / charts */
  risk_score?: number | null;
  heuristics_count?: number | null;
  /** Primary typology tag for queue display */
  typology_tag?: string | null;
}

/** Per-lens signal strengths 0–1 for table dots / radar */
export interface LensSignalScores {
  behavioral: number;
  graph: number;
  entity: number;
  temporal: number;
  offramp: number;
}

/** Extended row for dashboard / risk queue tables */
export interface TransactionQueueRow extends Transaction {
  typology_tag?: string | null;
  lens_scores?: LensSignalScores | null;
  /** Short label for queue, e.g. TX-8821 */
  display_ref?: string | null;
}

export interface TransactionScore {
  id: string;
  transaction_id: string;
  behavioral_score: number | null;
  behavioral_anomaly_score: number | null;
  graph_score: number | null;
  entity_score: number | null;
  temporal_score: number | null;
  offramp_score: number | null;
  meta_score: number | null;
  predicted_label: string | null;
  explanation_summary: string | null;
  scored_at: string;
}
