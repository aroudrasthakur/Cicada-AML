import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { ScoringMetrics, ScoringMode } from "@/types/dashboard";
import { fetchModelMetrics, fetchModelThreshold } from "@/api/runs";
import {
  fallbackScoringMetrics,
  ScoringModeCtx,
} from "@/contexts/scoringModeContext";

export function ScoringModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ScoringMode>("FULL_SCORING");
  const [metrics, setMetricsState] = useState<ScoringMetrics>(fallbackScoringMetrics);

  useEffect(() => {
    (async () => {
      try {
        const [mm, tc] = await Promise.all([
          fetchModelMetrics().catch(() => ({ metrics: null })),
          fetchModelThreshold().catch(() => ({ threshold: null })),
        ]);
        const prAuc = mm.metrics?.pr_auc ?? 0;
        const recall = tc.threshold?.recall_at_threshold ?? 0;
        const precision = tc.threshold?.precision_at_threshold ?? 0;
        setMetricsState({ precisionAt50: precision, recallAt50: recall, prAuc });
      } catch {
        /* keep fallback */
      }
    })();
  }, []);

  const setMetrics = useCallback((m: ScoringMetrics) => {
    setMetricsState(m);
  }, []);

  const value = useMemo(
    () => ({ mode, setMode, metrics, setMetrics }),
    [mode, metrics, setMetrics],
  );

  return (
    <ScoringModeCtx.Provider value={value}>{children}</ScoringModeCtx.Provider>
  );
}
