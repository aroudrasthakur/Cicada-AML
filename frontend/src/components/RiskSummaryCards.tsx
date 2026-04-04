import { AlertTriangle, FolderKanban, Shield } from "lucide-react";
import { formatNumber } from "../utils/formatters";

export interface RiskSummaryCardsProps {
  suspiciousTx: number;
  suspiciousWallets: number;
  networkCases: number;
  avgConfidence: number;
}

export default function RiskSummaryCards({
  suspiciousTx,
  suspiciousWallets,
  networkCases,
  avgConfidence,
}: RiskSummaryCardsProps) {
  const cards = [
    {
      label: "Suspicious transactions",
      value: formatNumber(suspiciousTx, 0),
      icon: AlertTriangle,
      iconClass: "text-amber-400",
    },
    {
      label: "Suspicious wallets",
      value: formatNumber(suspiciousWallets, 0),
      icon: AlertTriangle,
      iconClass: "text-amber-400",
    },
    {
      label: "Network cases",
      value: formatNumber(networkCases, 0),
      icon: FolderKanban,
      iconClass: "text-blue-400",
    },
    {
      label: "Avg. confidence",
      value: `${formatNumber(avgConfidence * 100, 1)}%`,
      icon: Shield,
      iconClass: "text-emerald-400",
    },
  ] as const;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map(({ label, value, icon: Icon, iconClass }) => (
        <div
          key={label}
          className="rounded-xl border border-gray-800 bg-gray-900 p-6 text-gray-100"
        >
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm font-medium text-gray-400">{label}</p>
            <Icon className={`h-5 w-5 shrink-0 ${iconClass}`} aria-hidden />
          </div>
          <p className="mt-4 text-3xl font-semibold tracking-tight tabular-nums">
            {value}
          </p>
        </div>
      ))}
    </div>
  );
}
