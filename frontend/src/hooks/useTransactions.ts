import { useCallback, useEffect, useState } from "react";
import { fetchTransactions } from "../api/transactions";
import type { Transaction } from "../types/transaction";

export function useTransactions(params?: {
  page?: number;
  limit?: number;
  label?: string;
  min_risk?: number;
}) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetchTransactions(params);
      setTransactions(resp.items);
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

  return { transactions, total, loading, error, refetch };
}
