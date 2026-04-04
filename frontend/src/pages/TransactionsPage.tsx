import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Eye,
  LayoutGrid,
  Loader2,
} from "lucide-react";
import TransactionTable from "@/components/TransactionTable";
import RunSelectorDropdown from "@/components/RunSelectorDropdown";
import { useRunContext } from "@/contexts/useRunContext";
import { useThresholds } from "@/contexts/ThresholdProvider";
import { fetchRunSuspicious, fetchRunReport } from "@/api/runs";
import type { TransactionQueueRow } from "@/types/transaction";
import { mapEnrichedSuspiciousToQueueRow } from "@/utils/suspiciousQueueRow";

const PAGE_SIZE_OPTIONS = [8, 10, 12] as const;

export default function TransactionsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const focus = searchParams.get("focus");
  const { runs } = useRunContext();
  const { config: tierConfig } = useThresholds();

  const completedRuns = useMemo(
    () => runs.filter((r) => r.status === "completed"),
    [runs],
  );
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [rows, setRows] = useState<TransactionQueueRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(10);

  useEffect(() => {
    if (!selectedRunId && completedRuns.length > 0) {
      setSelectedRunId(completedRuns[0].id);
    }
  }, [completedRuns, selectedRunId]);

  useEffect(() => {
    if (!selectedRunId) {
      setRows([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setPage(1);

    (async () => {
      try {
        const [sus, report] = await Promise.all([
          fetchRunSuspicious(selectedRunId),
          fetchRunReport(selectedRunId).catch(() => null),
        ]);
        if (cancelled) return;
        const topTxns = report?.content?.top_suspicious_transactions ?? [];

        const mapped: TransactionQueueRow[] = sus.map((t) => {
          const detail = topTxns.find(
            (d: { transaction_id: string }) => d.transaction_id === t.transaction_id,
          );
          return mapEnrichedSuspiciousToQueueRow(t, tierConfig, detail ?? null);
        });
        mapped.sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0));
        setRows(mapped);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e : new Error("Failed to load transactions"));
          setRows([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedRunId, tierConfig]);

  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));

  useEffect(() => {
    setPage((p) => Math.min(Math.max(1, p), totalPages));
  }, [totalPages, pageSize]);

  const paged = useMemo(() => {
    const start = (page - 1) * pageSize;
    return rows.slice(start, start + pageSize);
  }, [rows, page, pageSize]);

  const rangeStart = rows.length === 0 ? 0 : (page - 1) * pageSize + 1;
  const rangeEnd = Math.min(page * pageSize, rows.length);

  const pageNumbers = useMemo((): (number | "ellipsis")[] => {
    const total = totalPages;
    const cur = page;
    if (total <= 9) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }
    const set = new Set<number>();
    set.add(1);
    set.add(total);
    for (let i = cur - 1; i <= cur + 1; i++) {
      if (i >= 1 && i <= total) set.add(i);
    }
    const sorted = [...set].sort((a, b) => a - b);
    const out: (number | "ellipsis")[] = [];
    for (let i = 0; i < sorted.length; i++) {
      if (i > 0 && sorted[i] - sorted[i - 1] > 1) {
        out.push("ellipsis");
      }
      out.push(sorted[i]);
    }
    return out;
  }, [page, totalPages]);

  const selectedRunLabel =
    runs.find((r) => r.id === selectedRunId)?.label?.trim() || "Selected run";

  return (
    <div className="flex min-h-0 flex-col gap-5">
      {/* Header */}
      <section className="relative overflow-hidden rounded-2xl border border-[var(--color-aegis-border)] bg-gradient-to-br from-[#0d1117] via-[#0a0e14] to-[#060810] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]">
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#34d399]/45 to-transparent"
          aria-hidden
        />
        <div className="relative flex flex-wrap items-start justify-between gap-4 p-5 sm:p-6">
          <div className="flex min-w-0 items-start gap-3">
            <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[#34d399]/25 bg-[#34d399]/10 text-[#6ee7b7]">
              <LayoutGrid className="h-5 w-5" aria-hidden />
            </div>
            <div>
              <h1 className="font-display text-2xl font-bold tracking-tight text-[#e6edf3]">
                Transactions
              </h1>
              <p className="mt-1 max-w-xl font-data text-sm leading-relaxed text-[var(--color-aegis-muted)]">
                Suspicious transactions from the selected pipeline run
                one screen.
                {focus && (
                  <span className="ml-2 text-[var(--color-aegis-green)]">· focus {focus}</span>
                )}
              </p>
            </div>
          </div>
          <RunSelectorDropdown
            runs={runs}
            selectedRunId={selectedRunId}
            onSelect={(id) => setSelectedRunId(id)}
          />
        </div>
      </section>

      {loading && (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-[var(--color-aegis-border)] bg-[#0d1117]/80 py-20">
          <Loader2
            className="h-9 w-9 animate-spin text-[var(--color-aegis-green)]"
            aria-hidden
          />
          <p className="mt-4 font-data text-sm text-[var(--color-aegis-muted)]">
            Loading transactions…
          </p>
        </div>
      )}

      {!loading && error && (
        <div className="rounded-2xl border border-red-500/35 bg-red-950/25 px-5 py-4 font-data text-sm text-red-200">
          {error.message}
        </div>
      )}

      {!loading && !error && rows.length === 0 && (
        <div className="rounded-2xl border border-dashed border-[var(--color-aegis-border)] bg-[#0d1117]/50 px-6 py-16 text-center">
          <p className="font-data text-sm text-[#9aa7b8]">
            No suspicious transactions found for this run.
          </p>
        </div>
      )}

      {!loading && !error && rows.length > 0 && (
        <section className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-[var(--color-aegis-border)] bg-[#0a0e14]/80 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-aegis-border)] bg-[#060810]/60 px-4 py-3 sm:px-5">
            <div className="font-data text-xs text-[var(--color-aegis-muted)]">
              <span className="text-[#9aa7b8]">{selectedRunLabel}</span>
              <span className="mx-2 text-[#3d4a5c]">·</span>
              <span className="tabular-nums text-[#c8d4e0]">{rows.length}</span>{" "}
              suspicious
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label htmlFor="tx-page-size" className="font-data text-[11px] text-[var(--color-aegis-muted)]">
                Rows / page
              </label>
              <select
                id="tx-page-size"
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value) as (typeof PAGE_SIZE_OPTIONS)[number]);
                  setPage(1);
                }}
                className="rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117] px-2.5 py-1.5 font-data text-xs text-[#e6edf3] outline-none focus:border-[#34d399]/45"
              >
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-x-auto">
            <TransactionTable
              transactions={paged}
              variant="standard"
              compact
              embedded
              onSelect={(id) =>
                navigate(`/dashboard/transactions?focus=${encodeURIComponent(id)}`)
              }
            />
          </div>

          <footer className="flex flex-col gap-3 border-t border-[var(--color-aegis-border)] bg-[#060810]/50 px-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-4">
            <p className="text-center font-data text-[11px] text-[var(--color-aegis-muted)] sm:text-left">
              <span className="tabular-nums text-[#c8d4e0]">
                {rangeStart}–{rangeEnd}
              </span>{" "}
              of{" "}
              <span className="tabular-nums text-[#c8d4e0]">{rows.length}</span>
            </p>

            <div className="flex flex-wrap items-center justify-center gap-1 sm:justify-end">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage(1)}
                className="rounded-lg border border-transparent p-2 text-[#9aa7b8] hover:border-[var(--color-aegis-border)] hover:bg-[#0d1117] hover:text-[#e6edf3] disabled:opacity-30"
                aria-label="First page"
              >
                <ChevronsLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded-lg border border-transparent p-2 text-[#9aa7b8] hover:border-[var(--color-aegis-border)] hover:bg-[#0d1117] hover:text-[#e6edf3] disabled:opacity-30"
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>

              <div className="mx-1 flex flex-wrap items-center justify-center gap-1">
                {pageNumbers.map((item, i) =>
                  item === "ellipsis" ? (
                    <span
                      key={`ellipsis-${i}`}
                      className="px-1 font-data text-[11px] text-[#5c6b7e]"
                    >
                      …
                    </span>
                  ) : (
                    <button
                      key={item}
                      type="button"
                      onClick={() => setPage(item)}
                      className={`min-w-[2rem] rounded-lg px-2 py-1 font-data text-xs tabular-nums transition-colors ${
                        page === item
                          ? "border border-[#34d399]/35 bg-[#34d399]/15 text-[#6ee7b7]"
                          : "border border-transparent text-[#9aa7b8] hover:border-[var(--color-aegis-border)] hover:bg-[#0d1117] hover:text-[#e6edf3]"
                      }`}
                    >
                      {item}
                    </button>
                  ),
                )}
              </div>

              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="rounded-lg border border-transparent p-2 text-[#9aa7b8] hover:border-[var(--color-aegis-border)] hover:bg-[#0d1117] hover:text-[#e6edf3] disabled:opacity-30"
                aria-label="Next page"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage(totalPages)}
                className="rounded-lg border border-transparent p-2 text-[#9aa7b8] hover:border-[var(--color-aegis-border)] hover:bg-[#0d1117] hover:text-[#e6edf3] disabled:opacity-30"
                aria-label="Last page"
              >
                <ChevronsRight className="h-4 w-4" />
              </button>
            </div>
          </footer>
        </section>
      )}

      {!loading && !error && rows.length > 0 && (
        <p className="text-center font-data text-[11px] text-[var(--color-aegis-muted)] sm:text-left">
          <Link
            className="inline-flex items-center gap-1.5 text-[var(--color-aegis-green)] transition-colors hover:text-[#6ee7b7] hover:underline"
            to="/dashboard/explorer"
          >
            Open Flow Explorer
            <Eye className="h-3.5 w-3.5" aria-hidden />
          </Link>
        </p>
      )}
    </div>
  );
}
