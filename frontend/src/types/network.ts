export interface NetworkCase {
  id: string;
  case_name: string;
  typology: string | null;
  risk_score: number | null;
  total_amount: number | null;
  start_time: string | null;
  end_time: string | null;
  explanation: string | null;
  graph_snapshot_path: string | null;
  created_at: string;
  wallets?: string[];
}
