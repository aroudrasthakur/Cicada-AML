import { AlertTriangle, Loader2, Network } from "lucide-react";
import { useNetworkCases } from "../hooks/useNetworkCases";
import { formatNumber } from "../utils/formatters";

export default function NetworkCasesPage() {
  const { cases, loading, error } = useNetworkCases();

  return (
    <div className="px-8 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-white">Network Cases</h1>

      {loading && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-16 flex flex-col items-center justify-center text-gray-500">
          <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
          <p className="mt-3 text-sm">Loading network cases…</p>
        </div>
      )}

      {!loading && error && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 text-red-400 text-sm">
          {error.message}
        </div>
      )}

      {!loading && !error && cases.length === 0 && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-12 text-center">
          <Network
            className="h-12 w-12 text-gray-600 mx-auto mb-4"
            aria-hidden
          />
          <p className="text-gray-400 font-medium">No network cases yet</p>
          <p className="text-sm text-gray-500 mt-2 max-w-md mx-auto">
            Run network detection or import cases to see typologies, risk
            scores, and explanations here.
          </p>
        </div>
      )}

      {!loading && !error && cases.length > 0 && (
        <ul className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {cases.map((c) => (
            <li
              key={c.id}
              className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-white truncate">
                    {c.case_name}
                  </h2>
                  <p className="text-sm text-gray-500 mt-1">
                    {c.typology ?? "Unknown typology"}
                  </p>
                </div>
                <span className="inline-flex items-center gap-1 shrink-0 rounded-lg bg-amber-500/10 text-amber-400 text-xs font-medium px-2.5 py-1 border border-amber-500/20">
                  <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                  {c.risk_score != null
                    ? formatNumber(c.risk_score, 2)
                    : "—"}
                </span>
              </div>
              <div className="text-sm">
                <span className="text-gray-500">Total amount</span>
                <p className="text-gray-200 font-medium tabular-nums mt-0.5">
                  {c.total_amount != null
                    ? formatNumber(c.total_amount)
                    : "—"}
                </p>
              </div>
              <div className="text-sm">
                <span className="text-gray-500">Explanation</span>
                <p className="text-gray-300 mt-1 leading-relaxed">
                  {c.explanation ?? "No explanation available."}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
