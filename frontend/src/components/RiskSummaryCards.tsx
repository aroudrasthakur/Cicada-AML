import type { LucideIcon } from "lucide-react";
import { AlertTriangle, GitBranch, ShieldAlert, Zap } from "lucide-react";
import { formatNumber } from "@/utils/formatters";
import type { DashboardSummary } from "@/types/dashboard";
import { SparklineBars } from "./SparklineBars";

export type RiskSummaryCardsProps = DashboardSummary;

function deltaText(delta: number | undefined): string {
  if (delta == null || Number.isNaN(delta)) return "—";
  const sign = delta >= 0 ? "+" : "";
  return `${sign}${delta.toFixed(1)}%`;
}

function Card({
  label,
  value,
  icon: Icon,
  accent,
  sparkClass,
  borderAccent,
  delta,
  trendNote,
  seed,
}: {
  label: string;
  value: number;
  icon: LucideIcon;
  accent: string;
  sparkClass: string;
  borderAccent: string;
  delta?: number;
  trendNote?: string;
  seed: number;
}) {
  const subline =
    trendNote != null && trendNote.length > 0
      ? trendNote
      : `vs prior ${deltaText(delta)}`;

  return (
    <div
      className={`rounded-xl border border-[var(--color-aegis-border)] border-l-4 bg-[#0d1117] p-5 ${borderAccent}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-data text-[10px] uppercase tracking-wider text-[var(--color-aegis-muted)]">
            {label}
          </p>
          <p
            className={`mt-2 font-display text-3xl font-semibold tabular-nums tracking-tight ${accent}`}
          >
            {formatNumber(value, 0)}
          </p>
          <p className="mt-1 font-data text-[11px] text-[var(--color-aegis-muted)]">{subline}</p>
        </div>
        <Icon className="h-5 w-5 shrink-0 opacity-70" aria-hidden />
      </div>
      <SparklineBars seed={seed} colorClass={sparkClass} />
    </div>
  );
}

export default function RiskSummaryCards({
  criticalAlerts,
  txnsScored,
  networkCases,
  heuristicsFired,
  deltas,
  trends,
}: RiskSummaryCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card
        label="Critical alerts"
        value={criticalAlerts}
        icon={AlertTriangle}
        accent="text-[#f87171]/95"
        borderAccent="border-l-[#f87171]/55"
        sparkClass="bg-[#f87171]/80"
        delta={deltas?.criticalAlerts}
        trendNote={trends?.criticalAlerts}
        seed={0.12}
      />
      <Card
        label="Txns scored"
        value={txnsScored}
        icon={ShieldAlert}
        accent="text-[#34d399]/95"
        borderAccent="border-l-[#34d399]/50"
        sparkClass="bg-[#34d399]/75"
        delta={deltas?.txnsScored}
        trendNote={trends?.txnsScored}
        seed={0.45}
      />
      <Card
        label="Network cases"
        value={networkCases}
        icon={GitBranch}
        accent="text-[#a78bfa]/95"
        borderAccent="border-l-[#a78bfa]/55"
        sparkClass="bg-[#a78bfa]/70"
        delta={deltas?.networkCases}
        trendNote={trends?.networkCases}
        seed={0.67}
      />
      <Card
        label="Heuristics fired"
        value={heuristicsFired}
        icon={Zap}
        accent="text-[#fbbf24]/95"
        borderAccent="border-l-[#fbbf24]/50"
        sparkClass="bg-[#fbbf24]/70"
        delta={deltas?.heuristicsFired}
        trendNote={trends?.heuristicsFired}
        seed={0.89}
      />
    </div>
  );
}
