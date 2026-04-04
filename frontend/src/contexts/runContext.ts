import { createContext } from "react";
import type { PipelineRun } from "@/types/run";

export interface RunContextValue {
  /** Currently active / selected run */
  activeRun: PipelineRun | null;
  /** All historical runs (newest first) */
  runs: PipelineRun[];
  /** Select a different run by id */
  selectRun: (runId: string) => void;
  /** Refresh the run list from backend */
  refreshRuns: () => Promise<void>;
  /** Track a newly-created run and start polling */
  trackRun: (runId: string) => void;
  loading: boolean;
}

export const RunCtx = createContext<RunContextValue | null>(null);
