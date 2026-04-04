import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import type { Transaction } from "../types/transaction";
import {
  formatCurrency,
  formatDate,
  formatRiskLevel,
  truncateAddress,
} from "../utils/formatters";

export interface TransactionTableProps {
  transactions: Transaction[];
  onSelect?: (id: string) => void;
}

type SortKey =
  | "transaction_id"
  | "sender_wallet"
  | "receiver_wallet"
  | "amount"
  | "risk_score"
  | "heuristics_count"
  | "timestamp";

function riskBadgeClasses(score: number | null | undefined): string {
  if (score == null) {
    return "border border-gray-700 bg-gray-800/60 text-gray-400";
  }
  if (score >= 0.75) {
    return "border border-red-800 bg-red-950/50 text-red-300";
  }
  if (score >= 0.5) {
    return "border border-orange-800 bg-orange-950/40 text-orange-300";
  }
  if (score >= 0.25) {
    return "border border-yellow-800 bg-yellow-950/40 text-yellow-200";
  }
  return "border border-green-800 bg-green-950/40 text-green-300";
}

export default function TransactionTable({
  transactions,
  onSelect,
}: TransactionTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sorted = useMemo(() => {
    const dir = sortDir === "asc" ? 1 : -1;
    return [...transactions].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number") {
        return (av - bv) * dir;
      }
      return String(av).localeCompare(String(bv)) * dir;
    });
  }, [transactions, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "timestamp" ? "desc" : "asc");
    }
  }

  function SortHeader({
    label,
    columnKey,
  }: {
    label: string;
    columnKey: SortKey;
  }) {
    const active = sortKey === columnKey;
    return (
      <th className="px-4 py-3 font-medium">
        <button
          type="button"
          onClick={() => toggleSort(columnKey)}
          className="inline-flex items-center gap-1 text-gray-400 hover:text-gray-200"
        >
          {label}
          {active &&
            (sortDir === "asc" ? (
              <ArrowUp className="h-3.5 w-3.5" aria-hidden />
            ) : (
              <ArrowDown className="h-3.5 w-3.5" aria-hidden />
            ))}
        </button>
      </th>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-gray-800 bg-gray-900 text-gray-100">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 bg-gray-950/40 text-left">
              <SortHeader label="TX ID" columnKey="transaction_id" />
              <SortHeader label="Sender" columnKey="sender_wallet" />
              <SortHeader label="Receiver" columnKey="receiver_wallet" />
              <SortHeader label="Amount" columnKey="amount" />
              <SortHeader label="Risk score" columnKey="risk_score" />
              <SortHeader label="Heuristics" columnKey="heuristics_count" />
              <SortHeader label="Timestamp" columnKey="timestamp" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800 text-gray-300">
            {sorted.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  className="px-4 py-12 text-center text-gray-500"
                >
                  No transactions to display. Adjust filters or ingest data.
                </td>
              </tr>
            ) : (
              sorted.map((tx) => {
                const risk = tx.risk_score ?? null;
                const riskMeta = formatRiskLevel(risk);
                const riskLabel =
                  risk == null
                    ? "—"
                    : `${riskMeta.label} (${(risk * 100).toFixed(0)}%)`;
                return (
                  <tr
                    key={tx.id}
                    onClick={() => onSelect?.(tx.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect?.(tx.id);
                      }
                    }}
                    tabIndex={onSelect ? 0 : undefined}
                    role={onSelect ? "button" : undefined}
                    className={
                      onSelect
                        ? "cursor-pointer hover:bg-gray-800/60 focus-visible:bg-gray-800/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600/50"
                        : undefined
                    }
                  >
                    <td className="px-4 py-3 font-mono text-xs text-gray-200">
                      {truncateAddress(tx.transaction_id, 8)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {truncateAddress(tx.sender_wallet, 6)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {truncateAddress(tx.receiver_wallet, 6)}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-gray-200">
                      {formatCurrency(tx.amount)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${riskBadgeClasses(risk)}`}
                      >
                        {riskLabel}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex min-w-[2rem] justify-center rounded-md border border-gray-700 bg-gray-800/80 px-2 py-0.5 text-xs font-medium tabular-nums text-gray-200">
                        {tx.heuristics_count ?? "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {formatDate(tx.timestamp)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
