import { useCallback, useEffect, useState } from "react";
import { fetchNetworkCases } from "../api/networks";
import type { NetworkCase } from "../types/network";

export function useNetworkCases(params?: { page?: number; limit?: number }) {
  const [cases, setCases] = useState<NetworkCase[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetchNetworkCases(params);
      setCases(resp.items);
      setTotal(resp.total);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { cases, total, loading, error, refetch };
}
