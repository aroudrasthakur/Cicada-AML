import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Brain,
  GitBranch,
  ArrowLeftRight,
  Activity,
} from "lucide-react";

function RiskSummaryCard({
  title,
  value,
  icon: Icon,
}: {
  title: string;
  value: number;
  icon: LucideIcon;
}) {
  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-400">{title}</span>
        <Icon className="h-5 w-5 text-blue-400 shrink-0" aria-hidden />
      </div>
      <p className="text-3xl font-bold text-white tabular-nums">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <div className="px-8 py-6 space-y-8">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <RiskSummaryCard
          title="Suspicious Transactions"
          value={0}
          icon={ArrowLeftRight}
        />
        <RiskSummaryCard
          title="Suspicious Wallets"
          value={0}
          icon={AlertTriangle}
        />
        <RiskSummaryCard title="Network Cases" value={0} icon={GitBranch} />
        <RiskSummaryCard title="Model Confidence" value={0} icon={Brain} />
      </div>

      <section className="rounded-xl bg-gray-900 border border-gray-800 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="h-5 w-5 text-amber-400" aria-hidden />
          <h2 className="text-lg font-semibold text-white">
            Top Triggered Heuristics
          </h2>
        </div>
        <div className="rounded-lg border border-dashed border-gray-700 bg-gray-950/50 py-12 px-4 text-center text-sm text-gray-500">
          No heuristic triggers recorded yet. Run analysis to populate this
          section.
        </div>
      </section>

      <section className="rounded-xl bg-gray-900 border border-gray-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">
          Recent Suspicious Activity
        </h2>
        <div className="overflow-x-auto rounded-lg border border-gray-800">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-800">
                <th className="px-4 py-3 font-medium">Transaction</th>
                <th className="px-4 py-3 font-medium">Risk Score</th>
                <th className="px-4 py-3 font-medium">Typology</th>
                <th className="px-4 py-3 font-medium">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-gray-300">
              <tr>
                <td
                  colSpan={4}
                  className="px-4 py-10 text-center text-gray-500"
                >
                  No suspicious activity to display.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
