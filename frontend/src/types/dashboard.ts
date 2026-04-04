/** Dashboard / meta scoring UI types */

export type ScoringMode = "FULL_SCORING" | "HEURISTICS_ONLY";

export interface ScoringMetrics {
  precisionAt50: number;
  recallAt50: number;
  prAuc: number;
}

export interface DashboardMetricDeltas {
  criticalAlerts: number;
  txnsScored: number;
  networkCases: number;
  heuristicsFired: number;
}

/** Optional per-card trend copy (replaces “vs prior ±%” when set). */
export interface DashboardTrendNotes {
  criticalAlerts: string;
  txnsScored: string;
  networkCases: string;
  heuristicsFired: string;
}

export interface DashboardSummary {
  criticalAlerts: number;
  txnsScored: number;
  networkCases: number;
  heuristicsFired: number;
  deltas?: DashboardMetricDeltas;
  trends?: DashboardTrendNotes;
}

export interface LensScores5 {
  behavioral: number;
  graph: number;
  entity: number;
  temporal: number;
  offramp: number;
}

export interface ModelPerformanceMetric {
  name: string;
  prAuc: number;
  recall50: number;
  precision50: number;
  f1: number;
  fpPer1k: number;
}

export interface LiveAlertItem {
  id: string;
  level: "critical" | "high" | "medium";
  title: string;
  time: string;
}

export interface TriggeredHeuristicRow {
  id: string;
  typologyId: string;
  name: string;
  confidence: number;
  severity: "critical" | "high" | "medium" | "low";
}

export interface TypologyCategoryStat {
  category: string;
  count: number;
  fraction: number;
}

export interface TypologySample {
  id: string;
  label: string;
  badge: "CRITICAL" | "HIGH" | "AI-ENABLED";
}
