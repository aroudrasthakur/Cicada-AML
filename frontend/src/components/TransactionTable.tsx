import { useMemo, useState, type KeyboardEvent } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import type { TransactionQueueRow } from "@/types/transaction";
import {
  formatCurrency,
  formatDate,
  formatRiskLevel,
  truncateAddress,
} from "@/utils/formatters";
import { LensDots } from "./LensDots";

export interface TransactionTableProps {
  transactions: TransactionQueueRow[];
  onSelect?: (id: string) => void;
  /** Highlights the selected row (queue UX). */
  selectedId?: string | null;
  /** Queue layout: typology + lens dots + combined id/wallet column */
  variant?: "standard" | "queue";
}

type SortKey =
  | "transaction_id"
  | "sender_wallet"
  | "receiver_wallet"
  | "amount"
  | "risk_score"
  | "heuristics_count"
  | "timestamp"
  | "typology_tag";

function riskBarClasses(score: number | null | undefined): string {
  if (score == null) {
    return "bg-[#2d3748]";
  }
  if (score >= 0.75) return "bg-[var(--color-aegis-red)]";
  if (score >= 0.5) return "bg-[var(--color-aegis-amber)]";
  if (score >= 0.25) return "bg-[#fbbf24]";
  return "bg-[var(--color-aegis-green)]";
}

function riskBadgeClasses(score: number | null | undefined): string {
  if (score == null) {
    return "border border-[var(--color-aegis-border)] bg-[#0d1117] text-[var(--color-aegis-muted)]";
  }
  if (score >= 0.75) {
    return "border border-red-500/40 bg-red-950/40 text-[#ff8a9d]";
  }
  if (score >= 0.5) {
    return "border border-amber-500/30 bg-amber-950/30 text-[#fcd34d]";
  }
  if (score >= 0.25) {
    return "border border-yellow-500/20 bg-yellow-950/20 text-[#fde68a]";
  }
  return "border border-emerald-500/25 bg-emerald-950/25 text-[#6ee7b7]";
}

export default function TransactionTable({
  transactions,
  onSelect,
  selectedId = null,
  variant = "standard",
}: TransactionTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>(
    variant === "queue" ? "risk_score" : "timestamp",
  );
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
      setSortDir(key === "timestamp" || key === "risk_score" ? "desc" : "asc");
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
      <th className="px-4 py-3 font-data text-[11px] font-medium uppercase tracking-wide text-[var(--color-aegis-muted)]">
        <button
          type="button"
          onClick={() => toggleSort(columnKey)}
          className="inline-flex items-center gap-1 hover:text-[#e6edf3]"
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

  const colSpan = variant === "queue" ? 4 : 7;

  return (
    <div className="overflow-hidden rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] text-[#e6edf3]">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-aegis-border)] bg-[#060810]/80 text-left">
              {variant === "queue" ? (
                <>
                  <SortHeader label="Transaction" columnKey="transaction_id" />
                  <SortHeader label="Score" columnKey="risk_score" />
                  <SortHeader label="Typology" columnKey="typology_tag" />
                  <th className="px-4 py-3 font-data text-[11px] font-medium uppercase tracking-wide text-[var(--color-aegis-muted)]">
                    Lens
                  </th>
                </>
              ) : (
                <>
                  <SortHeader label="TX ID" columnKey="transaction_id" />
                  <SortHeader label="Sender" columnKey="sender_wallet" />
                  <SortHeader label="Receiver" columnKey="receiver_wallet" />
                  <SortHeader label="Amount" columnKey="amount" />
                  <SortHeader label="Risk" columnKey="risk_score" />
                  <SortHeader label="Heuristics" columnKey="heuristics_count" />
                  <SortHeader label="Timestamp" columnKey="timestamp" />
                </>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-aegis-border)] font-data text-xs text-[#c8d4e0]">
            {sorted.length === 0 ? (
              <tr>
                <td
                  colSpan={colSpan}
                  className="px-4 py-12 text-center text-[var(--color-aegis-muted)]"
                >
                  No transactions to display.
                </td>
              </tr>
            ) : (
              sorted.map((tx) => {
                const risk = tx.risk_score ?? null;
                const defaultLens = {
                  behavioral: 0.2,
                  graph: 0.2,
                  entity: 0.2,
                  temporal: 0.2,
                  offramp: 0.2,
                };
                const lens = tx.lens_scores ?? defaultLens;

                const selected = selectedId != null && tx.id === selectedId;
                const rowBase =
                  onSelect != null
                    ? "cursor-pointer hover:bg-[#060810]/90 focus-visible:bg-[#060810]/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#34d399]/40"
                    : "";
                const rowSelected = selected
                  ? "bg-[#060810]/95 ring-1 ring-inset ring-[#34d399]/35"
                  : "";

                const rowProps = onSelect
                  ? {
                      onClick: () => onSelect(tx.id),
                      onKeyDown: (e: KeyboardEvent<HTMLTableRowElement>) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onSelect(tx.id);
                        }
                      },
                      tabIndex: 0 as const,
                      role: "button" as const,
                      className: `${rowBase} ${rowSelected}`.trim(),
                    }
                  : {};

                if (variant === "queue") {
                  return (
                    <tr key={tx.id} {...rowProps}>
                      <td className="px-4 py-3">
                        <div className="font-mono text-[11px] text-[#e6edf3]">
                          {tx.display_ref ?? truncateAddress(tx.transaction_id, 10)}
                        </div>
                        <div className="mt-0.5 font-mono text-[10px] text-[var(--color-aegis-muted)]">
                          {truncateAddress(tx.transaction_id, 5)}…
                          {tx.transaction_id.slice(-3)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col gap-1.5 min-w-[100px]">
                          <span className="font-mono text-sm tabular-nums text-[#e6edf3]">
                            {risk == null ? "—" : risk.toFixed(2)}
                          </span>
                          <div className="h-1.5 w-full max-w-[140px] overflow-hidden rounded-full bg-[#060810]">
                            <div
                              className={`h-full rounded-full transition-all ${riskBarClasses(risk)}`}
                              style={{
                                width: `${Math.min(100, (risk ?? 0) * 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="rounded-full border border-[var(--color-aegis-border)] bg-[#060810] px-2.5 py-0.5 text-[10px] text-[#a5b4c8]">
                          {(tx.typology_tag ?? "—").replace(/^T-\d+\s*/, "")}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <LensDots scores={lens} />
                      </td>
                    </tr>
                  );
                }

                const riskMeta = formatRiskLevel(risk);
                const riskLabel =
                  risk == null
                    ? "—"
                    : `${riskMeta.label} (${(risk * 100).toFixed(0)}%)`;

                return (
                  <tr key={tx.id} {...rowProps}>
                    <td className="px-4 py-3 font-mono text-[11px] text-[#e6edf3]">
                      {truncateAddress(tx.transaction_id, 8)}
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {truncateAddress(tx.sender_wallet, 6)}
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {truncateAddress(tx.receiver_wallet, 6)}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-[#e6edf3]">
                      {formatCurrency(tx.amount)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-medium ${riskBadgeClasses(risk)}`}
                      >
                        {riskLabel}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex min-w-[2rem] justify-center rounded-md border border-[var(--color-aegis-border)] bg-[#060810] px-2 py-0.5 text-[11px] font-medium tabular-nums">
                        {tx.heuristics_count ?? "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[var(--color-aegis-muted)]">
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
