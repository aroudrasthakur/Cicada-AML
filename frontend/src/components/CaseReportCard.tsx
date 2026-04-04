import type { NetworkCase } from "../types/network";
import { formatCurrency, formatDate, formatNumber } from "../utils/formatters";

export interface CaseReportCardProps {
  case: NetworkCase;
}

function riskBarColor(score: number): string {
  if (score >= 0.75) return "bg-red-500";
  if (score >= 0.5) return "bg-orange-500";
  if (score >= 0.25) return "bg-yellow-500";
  return "bg-green-500";
}

export default function CaseReportCard({ case: networkCase }: CaseReportCardProps) {
  const risk = networkCase.risk_score ?? null;
  const riskPct =
    risk == null ? 0 : Math.min(100, Math.max(0, risk * 100));

  const excerptSource = networkCase.explanation ?? "";
  const excerpt =
    excerptSource.length > 200
      ? `${excerptSource.slice(0, 200)}…`
      : excerptSource;

  const rangeStart = networkCase.start_time
    ? formatDate(networkCase.start_time)
    : "—";
  const rangeEnd = networkCase.end_time
    ? formatDate(networkCase.end_time)
    : "—";

  return (
    <article className="rounded-xl border border-gray-800 bg-gray-900 p-6 text-gray-100">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">
            {networkCase.case_name}
          </h2>
          <div className="mt-2 flex flex-wrap gap-2">
            {networkCase.typology ? (
              <span className="inline-flex rounded-md border border-blue-800 bg-blue-950/50 px-2 py-0.5 text-xs font-medium text-blue-200">
                {networkCase.typology}
              </span>
            ) : (
              <span className="text-xs text-gray-500">No typology</span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6">
        <div className="flex items-center justify-between gap-2 text-sm">
          <span className="text-gray-400">Risk score</span>
          {risk == null ? (
            <span className="text-gray-500">—</span>
          ) : (
            <span className="tabular-nums text-gray-200">
              {formatNumber(risk, 2)}
            </span>
          )}
        </div>
        {risk != null && (
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-800">
            <div
              className={`h-full rounded-full ${riskBarColor(risk)}`}
              style={{ width: `${riskPct}%` }}
            />
          </div>
        )}
      </div>

      <dl className="mt-6 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-gray-500">Total amount</dt>
          <dd className="mt-0.5 tabular-nums text-gray-200">
            {networkCase.total_amount == null
              ? "—"
              : formatCurrency(networkCase.total_amount)}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500">Time range</dt>
          <dd className="mt-0.5 text-gray-200">
            {rangeStart} → {rangeEnd}
          </dd>
        </div>
      </dl>

      {excerpt && (
        <p className="mt-6 text-sm leading-relaxed text-gray-400">{excerpt}</p>
      )}

      <div className="mt-6">
        <button
          type="button"
          className="rounded-lg border border-gray-700 bg-gray-800 px-4 py-2 text-sm font-medium text-gray-100 hover:border-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-600/40"
        >
          View Details
        </button>
      </div>
    </article>
  );
}
