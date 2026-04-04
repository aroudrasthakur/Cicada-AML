export type EnvironmentFilter =
  | "all"
  | "traditional"
  | "blockchain"
  | "hybrid"
  | "ai_enabled";

export interface FilterState {
  dateFrom: string;
  dateTo: string;
  riskThreshold: number;
  typology: string;
  environment: EnvironmentFilter;
  search: string;
}
