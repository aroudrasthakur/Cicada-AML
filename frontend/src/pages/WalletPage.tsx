import { Loader2, Search, Wallet as WalletIcon, Network } from "lucide-react";
import { useParams } from "react-router-dom";
import { useWallet } from "../hooks/useWallet";
import { formatDate, formatNumber } from "../utils/formatters";

export default function WalletPage() {
  const { address } = useParams<{ address: string }>();
  const { wallet, loading, error } = useWallet(address);

  return (
    <div className="px-8 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-white">Wallet Investigation</h1>

      {!address && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 max-w-xl">
          <label
            htmlFor="wallet-search"
            className="block text-sm font-medium text-gray-300 mb-2"
          >
            Look up a wallet
          </label>
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500"
              aria-hidden
            />
            <input
              id="wallet-search"
              type="search"
              placeholder="Enter wallet address and navigate from transaction links…"
              className="w-full rounded-lg bg-gray-950 border border-gray-800 pl-10 pr-4 py-2.5 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-600/40 focus:border-blue-600"
            />
          </div>
          <p className="text-xs text-gray-500 mt-3">
            Open a wallet from the sidebar or append the address to{" "}
            <span className="font-mono text-gray-400">/wallets/&lt;address&gt;</span>
            .
          </p>
        </div>
      )}

      {address && (
        <>
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
            <div className="flex items-start gap-3 mb-4">
              <WalletIcon className="h-6 w-6 text-blue-400 shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <h2 className="text-lg font-semibold text-white">
                  Wallet details
                </h2>
                <p className="text-xs text-gray-500 font-mono break-all mt-1">
                  {address}
                </p>
              </div>
            </div>

            {loading && (
              <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
                <p className="mt-3 text-sm">Loading wallet…</p>
              </div>
            )}

            {!loading && error && (
              <p className="text-sm text-red-400">{error.message}</p>
            )}

            {!loading && !error && wallet && (
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                <div>
                  <dt className="text-gray-500">Chain</dt>
                  <dd className="text-gray-200 mt-1">
                    {wallet.chain_id ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Total in</dt>
                  <dd className="text-gray-200 mt-1 tabular-nums">
                    {formatNumber(wallet.total_in)}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Total out</dt>
                  <dd className="text-gray-200 mt-1 tabular-nums">
                    {formatNumber(wallet.total_out)}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">First seen</dt>
                  <dd className="text-gray-200 mt-1">
                    {wallet.first_seen ? formatDate(wallet.first_seen) : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Last seen</dt>
                  <dd className="text-gray-200 mt-1">
                    {wallet.last_seen ? formatDate(wallet.last_seen) : "—"}
                  </dd>
                </div>
              </dl>
            )}
          </div>

          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 min-h-[320px] flex flex-col">
            <div className="flex items-center gap-2 mb-4">
              <Network className="h-5 w-5 text-violet-400" aria-hidden />
              <h2 className="text-lg font-semibold text-white">
                Transaction graph
              </h2>
            </div>
            <div className="flex-1 rounded-lg border border-dashed border-gray-700 bg-gray-950/50 flex items-center justify-center text-sm text-gray-500 text-center px-6">
              Graph visualization will render here once graph data is wired up.
            </div>
          </div>
        </>
      )}
    </div>
  );
}
