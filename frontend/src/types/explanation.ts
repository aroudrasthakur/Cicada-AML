export interface TriggeredHeuristicExplanationItem {
  id: number;
  label?: string;
  confidence: number;
}

export interface LensContributions {
  behavioral: number;
  graph: number;
  entity: number;
  temporal: number;
  offramp: number;
}

/** Optional SHAP-style feature contributions for UI breakdown */
export interface ShapFeatureContribution {
  name: string;
  value: number;
}

export interface ExplanationDetail {
  summary?: string;
  heuristics?: TriggeredHeuristicExplanationItem[];
  lenses?: Partial<LensContributions>;
  /** Global feature attributions when available */
  shap?: ShapFeatureContribution[];
  patternType?: string;
  launderingStage?: string;
}
