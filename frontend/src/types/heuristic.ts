export interface HeuristicRegistryEntry {
  id: number;
  name: string;
  environment: "traditional" | "blockchain" | "hybrid" | "ai_enabled";
  lens_tags: string[];
  description: string;
  data_requirements: string[];
}

export interface HeuristicResult {
  transaction_id: string;
  heuristic_vector: number[];
  applicability_vector: string[];
  triggered_ids: number[];
  triggered_count: number;
  top_typology: string | null;
  top_confidence: number | null;
  explanations: Record<string, string>;
}
