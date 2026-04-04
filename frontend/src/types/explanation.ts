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
  document: number;
  offramp: number;
}

export interface ExplanationDetail {
  summary?: string;
  heuristics?: TriggeredHeuristicExplanationItem[];
  lenses?: Partial<LensContributions>;
  patternType?: string;
  launderingStage?: string;
}
