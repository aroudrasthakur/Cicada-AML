import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { PipelineRun } from "@/types/run";
import { fetchRun, fetchRuns } from "@/api/runs";
import { RunCtx } from "@/contexts/runContext";

export function RunProvider({ children }: { children: ReactNode }) {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [activeRun, setActiveRun] = useState<PipelineRun | null>(null);
  const [loading, setLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshRuns = useCallback(async () => {
    try {
      const { runs: list } = await fetchRuns();
      setRuns(list);
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    refreshRuns();
  }, [refreshRuns]);

  const selectRun = useCallback(
    (runId: string) => {
      const found = runs.find((r) => r.id === runId) ?? null;
      setActiveRun(found);
    },
    [runs],
  );

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const trackRun = useCallback(
    (runId: string) => {
      stopPolling();
      setLoading(true);

      const poll = async () => {
        try {
          const run = await fetchRun(runId);
          setActiveRun(run);
          setRuns((prev) => {
            const idx = prev.findIndex((r) => r.id === runId);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = run;
              return next;
            }
            return [run, ...prev];
          });
          if (run.status === "completed" || run.status === "failed") {
            stopPolling();
            setLoading(false);
            refreshRuns();
          }
        } catch {
          /* silent */
        }
      };

      poll();
      pollRef.current = setInterval(poll, 1500);
    },
    [stopPolling, refreshRuns],
  );

  useEffect(() => stopPolling, [stopPolling]);

  return (
    <RunCtx.Provider
      value={{ activeRun, runs, selectRun, refreshRuns, trackRun, loading }}
    >
      {children}
    </RunCtx.Provider>
  );
}
