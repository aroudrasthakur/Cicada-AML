export type RunStatus = "pending" | "running" | "completed" | "failed";

export interface ProgressLogEntry {
  t: string;
  msg: string;
}

export interface PipelineRun {
  id: string;
  /** Owner (Supabase auth user / profiles.id) */
  user_id?: string | null;
  label: string | null;
  status: RunStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  progress_pct: number;
  total_files: number;
  total_txns: number;
  suspicious_tx_count: number;
  suspicious_cluster_count: number;
  /** Latest human-readable pipeline phase */
  current_step?: string | null;
  /** Append-only step log for the UI */
  progress_log?: ProgressLogEntry[] | null;
  /** Transactions scored so far during ML phase */
  scoring_tx_done?: number | null;
  scoring_tx_total?: number | null;
  /** 0–5 workload indicator (maps scoring progress; 5 = all lens outputs applied) */
  lenses_completed?: number | null;
}

export interface RunCluster {
  id: string;
  run_id: string;
  label: string | null;
  typology: string | null;
  risk_score: number;
  total_amount: number;
  wallet_count: number;
  tx_count: number;
}

export interface RunSuspiciousTx {
  id: string;
  run_id: string;
  transaction_id: string;
  meta_score: number;
  risk_level: string;
  typology: string | null;
  cluster_id: string | null;
}

export interface RunReportContent {
  run_id: string;
  generated_at: string;
  summary: {
    total_files: number;
    total_transactions: number;
    suspicious_transactions: number;
    cluster_count: number;
    threshold_used: number;
  };
  top_suspicious_transactions: {
    transaction_id: string;
    meta_score: number;
    risk_level: string;
    typology: string | null;
    behavioral_score: number;
    graph_score: number;
    entity_score: number;
    temporal_score: number;
    offramp_score: number;
  }[];
  cluster_findings: {
    cluster_id: string;
    label: string;
    typology: string;
    risk_score: number;
    wallet_count: number;
    tx_count: number;
    total_amount: number;
  }[];
  score_distribution: Record<string, number>;
}

export interface RunReport {
  id: string;
  run_id: string;
  title: string;
  content: RunReportContent;
  generated_at: string;
}

export interface RunGraphSnapshot {
  id: string;
  run_id: string;
  cluster_id: string;
  elements: Record<string, unknown>[];
}
