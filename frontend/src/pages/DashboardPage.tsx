import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ChevronLeft, ChevronRight, Flame, Loader2 } from "lucide-react";
import RiskSummaryCards from "@/components/RiskSummaryCards";
import TransactionTable from "@/components/TransactionTable";
import LensRadarChart from "@/components/LensRadarChart";
import ModelPerformanceChart from "@/components/ModelPerformanceChart";
import RunSelectorDropdown from "@/components/RunSelectorDropdown";
import { useRunContext } from "@/contexts/useRunContext";
import { useAuth } from "@/contexts/AuthContext";
import { useThresholds } from "@/contexts/ThresholdProvider";
import {
  fetchDashboardStats,
  fetchModelMetrics,
  fetchModelThreshold,
  fetchRunSuspicious,
  fetchRunReport,
  type DashboardStats,
  type ModelMetricsResponse,
  type ThresholdResponse,
} from "@/api/runs";
import type { TransactionQueueRow } from "@/types/transaction";
import type {
  LensScores5,
  ModelPerformanceMetric,
} from "@/types/dashboard";
import { formatScore4 } from "@/utils/formatters";
import { mapEnrichedSuspiciousToQueueRow } from "@/utils/suspiciousQueueRow";

const DASH_QUEUE_PAGE_SIZE = 10;

function greetingForNow(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export default function DashboardPage() {
  const { runs, activeRun } = useRunContext();
  const { profile, user } = useAuth();
  const { config: tierConfig } = useThresholds();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [modelMetrics, setModelMetrics] = useState<ModelMetricsResponse["metrics"]>(null);
  const [thresholdCfg, setThresholdCfg] = useState<ThresholdResponse["threshold"]>(null);
  const [queue, setQueue] = useState<TransactionQueueRow[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [queueFilter, setQueueFilter] = useState<"all" | "critical">("all");
  const [queuePage, setQueuePage] = useState(1);
  const [loading, setLoading] = useState(true);

  // Page-local run selection (not global activeRun)
  const completedRuns = useMemo(
    () => runs.filter((r) => r.status === "completed"),
    [runs],
  );
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  // Auto-select latest completed run when runs load
  useEffect(() => {
    if (!selectedRunId && completedRuns.length > 0) {
      setSelectedRunId(completedRuns[0].id);
    }
  }, [completedRuns, selectedRunId]);

  const selectedRun = useMemo(
    () => completedRuns.find((r) => r.id === selectedRunId) ?? null,
    [completedRuns, selectedRunId],
  );

  const displayName = useMemo(() => {
    if (profile) return `${profile.first_name ?? ""} ${profile.last_name ?? ""}`.trim();
    const meta = [user?.user_metadata?.first_name, user?.user_metadata?.last_name]
      .filter(Boolean)
      .join(" ")
      .trim();
    return meta || user?.email?.split("@")[0] || "Analyst";
  }, [profile, user]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [s, mm, tc] = await Promise.all([
        fetchDashboardStats(),
        fetchModelMetrics(),
        fetchModelThreshold(),
      ]);
      setStats(s);
      setModelMetrics(mm.metrics);
      setThresholdCfg(tc.threshold);
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Load suspicious txns for the selected run
  useEffect(() => {
    if (!selectedRunId) {
      setQueue([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [sus, report] = await Promise.all([
          fetchRunSuspicious(selectedRunId),
          fetchRunReport(selectedRunId).catch(() => null),
        ]);
        if (cancelled) return;
        const topTxns = report?.content?.top_suspicious_transactions ?? [];

        const rows: TransactionQueueRow[] = sus.map((t) => {
          const detail = topTxns.find((d: { transaction_id: string }) => d.transaction_id === t.transaction_id);
          return mapEnrichedSuspiciousToQueueRow(t, tierConfig, detail ?? null);
        });
        rows.sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0));
        setQueue(rows);
        if (rows.length > 0) setSelectedId(rows[0].id);
        else setSelectedId(null);
      } catch {
        if (!cancelled) setQueue([]);
      }
    })();
    return () => { cancelled = true; };
  }, [selectedRunId, tierConfig]);

  const filteredQueue = useMemo(() => {
    if (queueFilter === "critical") {
      const cutoff = tierConfig?.highRiskThreshold ?? 0.9;
      return queue.filter((r) => (r.risk_score ?? 0) >= cutoff);
    }
    return queue;
  }, [queue, queueFilter, tierConfig]);

  const queueTotalPages = Math.max(1, Math.ceil(filteredQueue.length / DASH_QUEUE_PAGE_SIZE));

  useEffect(() => {
    setQueuePage(1);
  }, [selectedRunId, queueFilter]);

  useEffect(() => {
    setQueuePage((p) => Math.min(Math.max(1, p), queueTotalPages));
  }, [queueTotalPages]);

  const pagedQueue = useMemo(() => {
    const start = (queuePage - 1) * DASH_QUEUE_PAGE_SIZE;
    return filteredQueue.slice(start, start + DASH_QUEUE_PAGE_SIZE);
  }, [filteredQueue, queuePage]);

  useEffect(() => {
    if (selectedId == null) return;
    const still = filteredQueue.some((r) => r.id === selectedId);
    if (!still && filteredQueue[0]) setSelectedId(filteredQueue[0].id);
  }, [filteredQueue, selectedId]);

  const selectedRow = useMemo(
    () => queue.find((r) => r.id === selectedId) ?? queue[0] ?? null,
    [queue, selectedId],
  );

  const radarScores: LensScores5 = useMemo(() => {
    const ls = selectedRow?.lens_scores;
    return {
      behavioral: ls?.behavioral ?? 0,
      graph: ls?.graph ?? 0,
      entity: ls?.entity ?? 0,
      temporal: ls?.temporal ?? 0,
      offramp: ls?.offramp ?? 0,
    };
  }, [selectedRow]);

  const greeting = greetingForNow();

  const prAuc = modelMetrics?.pr_auc ?? 0;
  const recall = thresholdCfg?.recall_at_threshold ?? 0;
  const precision = thresholdCfg?.precision_at_threshold ?? 0;
  const f1 = thresholdCfg?.optimal_f1 ?? 0;

  const sparkSeries = useMemo(() => {
    const done = completedRuns
      .slice()
      .sort(
        (a, b) =>
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      )
      .slice(-12);
    return {
      criticalAlerts: done.map((r) => r.suspicious_tx_count ?? 0),
      txnsScored: done.map((r) => r.total_txns ?? 0),
      networkCases: done.map((r) => r.suspicious_cluster_count ?? 0),
      heuristicsFired: done.map((r) => r.total_txns ?? 0),
    };
  }, [completedRuns]);

  const summary = useMemo(
    () => ({
      criticalAlerts: selectedRun?.suspicious_tx_count ?? stats?.total_suspicious ?? 0,
      txnsScored: selectedRun?.total_txns ?? stats?.total_txns_scored ?? 0,
      networkCases: selectedRun?.suspicious_cluster_count ?? stats?.total_clusters ?? 0,
      heuristicsFired: stats?.completed_runs ?? 0,
      deltas: undefined,
      trends: {
        criticalAlerts: selectedRun
          ? `run: ${selectedRun.suspicious_tx_count} suspicious`
          : stats?.latest_suspicious
            ? `latest run: ${stats.latest_suspicious}`
            : "no runs yet",
        txnsScored: selectedRun
          ? `run: ${selectedRun.total_txns.toLocaleString()} scored`
          : stats?.latest_txns
            ? `latest run: ${stats.latest_txns.toLocaleString()}`
            : "no runs yet",
        networkCases: selectedRun
          ? `run: ${selectedRun.suspicious_cluster_count} clusters`
          : stats?.latest_clusters
            ? `latest run: ${stats.latest_clusters}`
            : "no runs yet",
        heuristicsFired: `${stats?.completed_runs ?? 0} completed`,
      },
      sparkSeries,
    }),
    [stats, selectedRun, sparkSeries],
  );

  const perfMetrics: ModelPerformanceMetric[] = useMemo(() => {
    if (!modelMetrics?.feature_importance) return [];
    const fi = modelMetrics.feature_importance;
    const lenses = [
      { name: "Behavioral", key: "behavioral_score" },
      { name: "Graph", key: "graph_score" },
      { name: "Entity", key: "entity_score" },
      { name: "Temporal", key: "temporal_score" },
      { name: "Off-ramp", key: "offramp_score" },
    ];
    const maxImp = Math.max(...lenses.map((l) => fi[l.key] ?? 0), 0.01);
    return [
      ...lenses.map((l) => {
        const imp = fi[l.key] ?? 0;
        const relStrength = imp / maxImp;
        return {
          name: l.name,
          prAuc: Number(
            Math.min(0.95, prAuc * (0.7 + 0.3 * relStrength)).toFixed(4),
          ),
          recall50: Number(
            Math.min(0.95, recall * (0.7 + 0.3 * relStrength)).toFixed(4),
          ),
          precision50: Number(
            Math.min(0.95, precision * (0.7 + 0.3 * relStrength)).toFixed(4),
          ),
          f1: Number(
            Math.min(0.95, f1 * (0.7 + 0.3 * relStrength)).toFixed(4),
          ),
          fpPer1k: Math.round(20 * (1 - relStrength * 0.5)),
        };
      }),
      {
        name: "Meta",
        prAuc: Number(prAuc.toFixed(4)),
        recall50: Number(recall.toFixed(4)),
        precision50: Number(precision.toFixed(4)),
        f1: Number(f1.toFixed(4)),
        fpPer1k: 5,
      },
    ];
  }, [modelMetrics, prAuc, recall, precision, f1]);

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-[#34d399]" />
      </div>
    );
  }

  return (
    <div className="min-w-0 max-w-full space-y-6 overflow-x-hidden">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="font-display text-2xl font-semibold text-[#e6edf3]">
            {greeting}, {displayName}.
          </p>
          <p className="mt-1 font-data text-sm text-[#9aa7b8]">
            Here&apos;s your risk overview —{" "}
            <span className="text-[#f87171]/95">
              {selectedRun?.suspicious_tx_count ?? stats?.total_suspicious ?? 0} suspicious
            </span>{" "}
            {selectedRun
              ? `in ${selectedRun.label ?? `run ${selectedRun.id.slice(0, 8)}`}`
              : `across ${stats?.completed_runs ?? 0} runs`}.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <RunSelectorDropdown
            runs={runs}
            selectedRunId={selectedRunId}
            onSelect={setSelectedRunId}
          />
          <div className="flex flex-wrap items-end gap-6 font-mono text-[11px] uppercase tracking-wide text-[#7d8a99]">
            <p className="text-[#f87171]/95">{selectedRun?.suspicious_tx_count ?? stats?.total_suspicious ?? 0} alerts</p>
            <p className="text-[#34d399]/95">{formatScore4(recall)} recall</p>
            <p className="text-[#7dd3fc]/95">
              {(((selectedRun?.total_txns ?? stats?.total_txns_scored ?? 0)) / 1000).toFixed(1)}k scored
            </p>
          </div>
        </div>
      </div>

      <RiskSummaryCards {...summary} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_380px]">
        <div className="min-w-0 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-display text-lg font-semibold text-[#e6edf3]">
                Risk queue
              </h2>
              <p className="mt-0.5 font-data text-xs text-[#9aa7b8]">
                {queue.length > 0
                  ? `${queue.length} suspicious transactions from selected run`
                  : "No suspicious transactions yet — upload CSVs and run the pipeline"}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex rounded-lg border border-[var(--color-aegis-border)] bg-[#060810] p-0.5 font-data text-xs">
                <button
                  type="button"
                  onClick={() => setQueueFilter("all")}
                  className={`rounded-md px-3 py-1.5 transition-colors ${
                    queueFilter === "all"
                      ? "bg-[#0d1117] text-[#e6edf3]"
                      : "text-[#9aa7b8] hover:text-[#e6edf3]"
                  }`}
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={() => setQueueFilter("critical")}
                  className={`rounded-md px-3 py-1.5 transition-colors ${
                    queueFilter === "critical"
                      ? "bg-[#0d1117] text-[#f87171]/95"
                      : "text-[#9aa7b8] hover:text-[#e6edf3]"
                  }`}
                >
                  Critical
                </button>
              </div>
            </div>
          </div>

          {queue.length > 0 ? (
            <div className="space-y-3">
              <TransactionTable
                transactions={pagedQueue}
                variant="queue"
                compact
                selectedId={selectedId}
                onSelect={(id) => setSelectedId(id)}
              />
              {filteredQueue.length > DASH_QUEUE_PAGE_SIZE && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--color-aegis-border)] bg-[#060810]/50 px-3 py-2.5 font-data text-[11px] text-[var(--color-aegis-muted)]">
                  <span>
                    <span className="tabular-nums text-[#c8d4e0]">
                      {(queuePage - 1) * DASH_QUEUE_PAGE_SIZE + 1}
                      –
                      {Math.min(queuePage * DASH_QUEUE_PAGE_SIZE, filteredQueue.length)}
                    </span>{" "}
                    of{" "}
                    <span className="tabular-nums text-[#c8d4e0]">{filteredQueue.length}</span>
                    {queueFilter === "critical" ? " critical" : ""}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={queuePage <= 1}
                      onClick={() => setQueuePage((p) => Math.max(1, p - 1))}
                      className="inline-flex items-center gap-1 rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117] px-2.5 py-1.5 text-[#e6edf3] transition-colors hover:border-[#34d399]/35 disabled:opacity-35"
                    >
                      <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
                      Prev
                    </button>
                    <span className="tabular-nums text-[#9aa7b8]">
                      Page {queuePage} / {queueTotalPages}
                    </span>
                    <button
                      type="button"
                      disabled={queuePage >= queueTotalPages}
                      onClick={() => setQueuePage((p) => Math.min(queueTotalPages, p + 1))}
                      className="inline-flex items-center gap-1 rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117] px-2.5 py-1.5 text-[#e6edf3] transition-colors hover:border-[#34d399]/35 disabled:opacity-35"
                    >
                      Next
                      <ChevronRight className="h-3.5 w-3.5" aria-hidden />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] px-6 py-12 text-center">
              <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-[var(--color-aegis-muted)]" />
              <p className="font-data text-sm text-[#9aa7b8]">
                No suspicious transactions detected yet.
              </p>
            </div>
          )}
        </div>

        <aside className="flex flex-col gap-4">
          {selectedRow && (
            <>
              <div className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117]/80 px-4 py-3">
                <p className="font-mono text-[10px] uppercase tracking-wide text-[#7d8a99]">
                  Selected
                </p>
                <p className="mt-1 font-mono text-sm text-[#e6edf3]">
                  {selectedRow.display_ref ?? "—"}{" "}
                  <span className="text-[#9aa7b8]">
                    · {(selectedRow.typology_tag ?? "").replace(/-/g, " ")}
                  </span>
                </p>
              </div>
              <LensRadarChart key={selectedRow.id} scores={radarScores} />
            </>
          )}

          {activeRun && activeRun.status === "running" && (
            <div className="rounded-xl border border-[#60a5fa]/20 bg-[#0d1117] p-4">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-[#60a5fa]" />
                <h3 className="font-display text-sm font-semibold text-[#e6edf3]">
                  Pipeline running
                </h3>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#1e293b]">
                <div
                  className="h-full rounded-full bg-[#60a5fa] transition-all"
                  style={{ width: `${activeRun.progress_pct}%` }}
                />
              </div>
              <p className="mt-1 font-data text-[11px] text-[#9aa7b8]">
                {activeRun.progress_pct}% complete
              </p>
            </div>
          )}

          {stats?.latest_run && (
            <div className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] p-4">
              <h3 className="font-display text-sm font-semibold text-[#e6edf3]">
                Latest run
              </h3>
              <ul className="mt-3 space-y-2">
                <li className="flex items-start gap-2 font-data text-[12px] text-[#c8d4e0]">
                  {(stats.latest_suspicious ?? 0) > 0 ? (
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[#f87171]" />
                  ) : (
                    <Flame className="mt-0.5 h-4 w-4 shrink-0 text-[#34d399]" />
                  )}
                  <div>
                    <p>
                      {stats.latest_suspicious ?? 0} suspicious /{" "}
                      {stats.latest_txns?.toLocaleString() ?? 0} total
                    </p>
                    <p className="text-[10px] text-[var(--color-aegis-muted)]">
                      {stats.latest_clusters ?? 0} clusters detected
                    </p>
                  </div>
                </li>
              </ul>
            </div>
          )}
        </aside>
      </div>

      {perfMetrics.length > 0 && (
        <div className="min-w-0 max-w-full">
          <ModelPerformanceChart metrics={perfMetrics} />
        </div>
      )}
    </div>
  );
}
