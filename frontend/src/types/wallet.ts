export interface Wallet {
  id: string;
  wallet_address: string;
  chain_id: string | null;
  first_seen: string | null;
  last_seen: string | null;
  total_in: number;
  total_out: number;
  created_at: string;
}

export interface WalletScore {
  id: string;
  wallet_address: string;
  risk_score: number | null;
  fan_in_score: number | null;
  fan_out_score: number | null;
  velocity_score: number | null;
  exposure_score: number | null;
  scored_at: string;
}
