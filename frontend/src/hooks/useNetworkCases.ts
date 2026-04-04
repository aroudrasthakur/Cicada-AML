import { useCallback, useEffect, useState } from "react";
import { fetchNetworkCases } from "../api/networks";
import type { NetworkCase } from "../types/network";

export function useNetworkCases(params?: { page?: number; limit?: number }) {
  const [cases, setCases] = useState<NetworkCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchNetworkCases(params);
      setCases(data);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setLoading(false);
    }
  }, [params?.page, params?.limit]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { cases, loading, error, refetch };
}
