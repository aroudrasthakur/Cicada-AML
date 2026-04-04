import { useEffect, useState } from "react";
import { fetchWallet } from "../api/wallets";
import type { Wallet } from "../types/wallet";

export function useWallet(address: string | undefined) {
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!address?.trim()) {
      setWallet(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    const resolved = address.trim();

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchWallet(resolved);
        if (!cancelled) setWallet(data);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e : new Error(String(e)));
          setWallet(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [address]);

  return { wallet, loading, error };
}
