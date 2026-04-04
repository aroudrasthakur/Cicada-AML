import { Eye, Loader2, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { useTransactions } from "../hooks/useTransactions";
import { formatNumber, truncateAddress } from "../utils/formatters";

export default function TransactionsPage() {
  const { transactions, loading, error } = useTransactions();

  return (
    <div className="px-8 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-white">Transaction Analysis</h1>

      <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
        <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
          <div className="relative flex-1">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500"
              aria-hidden
            />
            <input
              type="search"
              placeholder="Search by transaction ID, wallet, or label…"
              className="w-full rounded-lg bg-gray-950 border border-gray-800 pl-10 pr-4 py-2.5 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-600/40 focus:border-blue-600"
              disabled
              readOnly
              aria-label="Search (coming soon)"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              disabled
              className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-800 text-gray-500 border border-gray-700 cursor-not-allowed"
            >
              Filters
            </button>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Search and filters will connect to the API in a later iteration.
        </p>
      </div>

      <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-800 bg-gray-950/40">
                <th className="px-4 py-3 font-medium">TX ID</th>
                <th className="px-4 py-3 font-medium">Sender</th>
                <th className="px-4 py-3 font-medium">Receiver</th>
                <th className="px-4 py-3 font-medium">Amount</th>
                <th className="px-4 py-3 font-medium">Risk Score</th>
                <th className="px-4 py-3 font-medium">Heuristics Triggered</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-gray-300">
              {loading && (
                <tr>
                  <td colSpan={7} className="px-4 py-16 text-center">
                    <Loader2
                      className="h-8 w-8 text-blue-400 animate-spin mx-auto"
                      aria-hidden
                    />
                    <p className="mt-3 text-gray-500">Loading transactions…</p>
                  </td>
                </tr>
              )}
              {!loading && error && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-red-400">
                    {error.message}
                  </td>
                </tr>
              )}
              {!loading && !error && transactions.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-gray-500">
                    No transactions found. Ingest or score data to see results
                    here.
                  </td>
                </tr>
              )}
              {!loading &&
                !error &&
                transactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-gray-800/40">
                    <td className="px-4 py-3 font-mono text-xs text-gray-200">
                      {truncateAddress(tx.transaction_id, 8)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {truncateAddress(tx.sender_wallet, 6)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {truncateAddress(tx.receiver_wallet, 6)}
                    </td>
                    <td className="px-4 py-3 tabular-nums">
                      {formatNumber(tx.amount)}
                    </td>
                    <td className="px-4 py-3 text-gray-500">—</td>
                    <td className="px-4 py-3 text-gray-500">—</td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/explorer?tx=${encodeURIComponent(tx.transaction_id)}`}
                        className="inline-flex items-center gap-1.5 text-blue-400 hover:text-blue-300 text-xs font-medium"
                      >
                        <Eye className="h-3.5 w-3.5" aria-hidden />
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
