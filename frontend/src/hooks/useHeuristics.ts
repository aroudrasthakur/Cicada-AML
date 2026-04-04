import { useEffect, useState } from "react";
import { fetchHeuristicResults } from "../api/heuristics";
import type { HeuristicResult } from "../types/heuristic";

export function useHeuristics(transactionId: string | undefined) {
  const [results, setResults] = useState<HeuristicResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!transactionId?.trim()) {
      setResults(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    const id = transactionId.trim();

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchHeuristicResults(id);
        if (!cancelled) setResults(data);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e : new Error(String(e)));
          setResults(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [transactionId]);

  return { results, loading, error };
}
