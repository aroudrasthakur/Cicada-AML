import { createContext } from "react";
import type { ScoringMetrics, ScoringMode } from "@/types/dashboard";

export interface ScoringModeContextValue {
  mode: ScoringMode;
  setMode: (m: ScoringMode) => void;
  metrics: ScoringMetrics;
  setMetrics: (m: ScoringMetrics) => void;
}

export const fallbackScoringMetrics: ScoringMetrics = {
  precisionAt50: 0,
  recallAt50: 0,
  prAuc: 0,
};

export const ScoringModeCtx = createContext<ScoringModeContextValue | null>(null);
