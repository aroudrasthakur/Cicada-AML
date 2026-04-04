import { useCallback, useEffect, useMemo, useState } from "react";
import {
  FileText,
  ChevronRight,
  ArrowLeft,
  AlertTriangle,
  BarChart3,
  Shield,
  Loader2,
} from "lucide-react";
import { useRunContext } from "@/contexts/useRunContext";
import { useThresholds } from "@/contexts/ThresholdProvider";
import { fetchRunClusters, fetchRunReport } from "@/api/runs";
import type { PipelineRun, RunCluster, RunReport, RunReportContent } from "@/types/run";
import type { RiskTierConfig } from "@/utils/riskTiers";
import {
  resolveRiskTier,
  riskTierBadgeClass,
  riskTierLabel,
} from "@/utils/riskTiers";
import ReportSummaryPanel from "@/components/ReportSummaryPanel";

export default function ReportsPage() {
  const { runs, selectRun } = useRunContext();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [report, setReport] = useState<RunReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const completedRuns = runs.filter((r) => r.status === "completed");

  const openReport = useCallback(async (runId: string) => {
    setSelectedRunId(runId);
    setLoading(true);
    setError(null);
    try {
      const r = await fetchRunReport(runId);
      setReport(r);
    } catch {
      setError("Failed to load report");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedRunId) selectRun(selectedRunId);
  }, [selectedRunId, selectRun]);

  if (selectedRunId && report && !loading) {
    return <ReportDetail report={report} onBack={() => setSelectedRunId(null)} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-[#e6edf3]">Reports</h1>
        <p className="font-data text-sm text-[var(--color-aegis-muted)]">
          One report per completed pipeline run
        </p>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-[#34d399]" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-[#f87171]/30 bg-[#f87171]/5 px-4 py-3 font-data text-sm text-[#fca5a5]">
          {error}
        </div>
      )}

      {!loading && completedRuns.length === 0 && (
        <div className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] px-4 py-16 text-center">
          <FileText className="mx-auto mb-3 h-10 w-10 text-[var(--color-aegis-muted)]" />
          <p className="font-display font-medium text-[#c8d4e0]">No reports yet</p>
          <p className="mx-auto mt-2 max-w-sm text-sm text-[#9aa7b8]">
            Upload CSVs and run the pipeline to generate a report.
          </p>
        </div>
      )}

      {!loading && completedRuns.length > 0 && (
        <div className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] overflow-hidden">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-aegis-border)] bg-[#060810]/80 text-left font-data text-[11px] uppercase tracking-wide text-[var(--color-aegis-muted)]">
                <th className="px-4 py-3">Run</th>
                <th className="px-4 py-3">Completed</th>
                <th className="px-4 py-3">Transactions</th>
                <th className="px-4 py-3">Suspicious</th>
                <th className="px-4 py-3">Clusters</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-aegis-border)] font-data text-[#c8d4e0]">
              {completedRuns.map((r) => (
                <RunRow key={r.id} run={r} onOpen={openReport} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RunRow({ run, onOpen }: { run: PipelineRun; onOpen: (id: string) => void }) {
  return (
    <tr
      className="cursor-pointer hover:bg-[#060810]/90"
      onClick={() => onOpen(run.id)}
    >
      <td className="px-4 py-3 font-medium text-[#e6edf3]">
        {run.label || `Run ${run.id.slice(0, 8)}`}
      </td>
      <td className="px-4 py-3 text-[var(--color-aegis-muted)]">
        {run.completed_at
          ? new Date(run.completed_at).toLocaleString()
          : "—"}
      </td>
      <td className="px-4 py-3 tabular-nums">{run.total_txns}</td>
      <td className="px-4 py-3 tabular-nums text-[#f87171]">
        {run.suspicious_tx_count}
      </td>
      <td className="px-4 py-3 tabular-nums">{run.suspicious_cluster_count}</td>
      <td className="px-4 py-3 text-right">
        <ChevronRight className="inline h-4 w-4 text-[#6b7c90]" />
      </td>
    </tr>
  );
}

function ReportDetail({
  report,
  onBack,
}: {
  report: RunReport;
  onBack: () => void;
}) {
  const { config: tierConfig } = useThresholds();
  const c: RunReportContent = report.content;
  const s = c.summary;
  const [liveClusters, setLiveClusters] = useState<RunCluster[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchRunClusters(report.run_id)
      .then((rows) => {
        if (!cancelled) setLiveClusters(rows);
      })
      .catch(() => {
        if (!cancelled) setLiveClusters(null);
      });
    return () => {
      cancelled = true;
    };
  }, [report.run_id]);

  const clusterFindings = useMemo(() => {
    const byId = new Map((liveClusters ?? []).map((row) => [row.id, row]));
    return c.cluster_findings.map((cl) => ({
      ...cl,
      risk_score: byId.get(cl.cluster_id)?.risk_score ?? cl.risk_score,
    }));
  }, [c.cluster_findings, liveClusters]);

  return (
    <div className="space-y-6">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1 font-data text-sm text-[#9aa7b8] hover:text-[#e6edf3]"
      >
        <ArrowLeft className="h-4 w-4" /> Back to reports
      </button>

      <div>
        <h1 className="font-display text-2xl font-bold text-[#e6edf3]">{report.title}</h1>
        <p className="font-data text-sm text-[var(--color-aegis-muted)]">
          Generated {new Date(report.generated_at).toLocaleString()}
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Files" value={s.total_files} />
        <StatCard label="Transactions" value={s.total_transactions} />
        <StatCard label="Suspicious" value={s.suspicious_transactions} accent />
        <StatCard label="Clusters" value={s.cluster_count} />
      </div>

      <ReportSummaryPanel runId={report.run_id} />

      {/* Cluster findings — uses same meta-score scale + thresholds as Transactions */}
      {clusterFindings.length > 0 && (
        <Section
          icon={<Shield className="h-4 w-4 text-[#a78bfa]" />}
          title="Cluster Findings"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            {clusterFindings.map((cl) => (
              <div
                key={cl.cluster_id}
                className="rounded-lg border border-[var(--color-aegis-border)] bg-[#060810] p-4"
              >
                <p className="font-data text-sm font-medium text-[#e6edf3]">
                  {cl.label}
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-2 font-data text-xs text-[#9aa7b8]">
                  <span>{cl.typology}</span>
                  <span className="text-[#6b7c90]">·</span>
                  <ClusterRiskMeta
                    score={cl.risk_score}
                    tierConfig={tierConfig}
                  />
                </div>
                <div className="mt-2 flex gap-4 font-data text-[11px] text-[#7d8a99]">
                  <span>{cl.wallet_count} wallets</span>
                  <span>{cl.tx_count} txns</span>
                  <span>${cl.total_amount.toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Score distribution */}
      <Section
        icon={<BarChart3 className="h-4 w-4 text-[#60a5fa]" />}
        title="Score Distribution"
      >
        <div className="flex flex-wrap gap-4 font-data text-sm text-[#c8d4e0]">
          {Object.entries(c.score_distribution).map(([level, count]) => (
            <span key={level} className="flex items-center gap-1.5">
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${
                  level === "high"
                    ? "bg-[#f87171]"
                    : level === "medium"
                      ? "bg-[#facc15]"
                      : level === "medium-low"
                        ? "bg-[#60a5fa]"
                        : "bg-[#34d399]"
                }`}
              />
              {level}: {count}
            </span>
          ))}
        </div>
      </Section>

      {/* Top suspicious transactions */}
      {c.top_suspicious_transactions.length > 0 && (
        <Section
          icon={<AlertTriangle className="h-4 w-4 text-[#f87171]" />}
          title="Top Suspicious Transactions"
        >
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-aegis-border)] text-left font-data text-[11px] uppercase tracking-wide text-[var(--color-aegis-muted)]">
                  <th className="px-3 py-2">Transaction</th>
                  <th className="px-3 py-2">Score</th>
                  <th className="px-3 py-2">Risk</th>
                  <th className="px-3 py-2">Typology</th>
                  <th className="px-3 py-2">Behav.</th>
                  <th className="px-3 py-2">Graph</th>
                  <th className="px-3 py-2">Entity</th>
                  <th className="px-3 py-2">Temporal</th>
                  <th className="px-3 py-2">Offramp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-aegis-border)] font-data text-[#c8d4e0]">
                {c.top_suspicious_transactions.map((t) => (
                  <tr key={t.transaction_id}>
                    <td className="px-3 py-2 font-mono text-[11px] text-[#e6edf3]">
                      {t.transaction_id.length > 16
                        ? `${t.transaction_id.slice(0, 16)}…`
                        : t.transaction_id}
                    </td>
                    <td className="px-3 py-2 tabular-nums font-medium text-[#f87171]">
                      {t.meta_score.toFixed(4)}
                    </td>
                    <td className="px-3 py-2">
                      <RiskTierBadge
                        score={t.meta_score}
                        tierConfig={tierConfig}
                        backendLevel={t.risk_level}
                      />
                    </td>
                    <td className="px-3 py-2 text-[11px]">{t.typology ?? "—"}</td>
                    <td className="px-3 py-2 tabular-nums">{t.behavioral_score.toFixed(3)}</td>
                    <td className="px-3 py-2 tabular-nums">{t.graph_score.toFixed(3)}</td>
                    <td className="px-3 py-2 tabular-nums">{t.entity_score.toFixed(3)}</td>
                    <td className="px-3 py-2 tabular-nums">{t.temporal_score.toFixed(3)}</td>
                    <td className="px-3 py-2 tabular-nums">{t.offramp_score.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}
    </div>
  );
}

function ClusterRiskMeta({
  score,
  tierConfig,
}: {
  score: number;
  tierConfig: RiskTierConfig | null;
}) {
  const tier = resolveRiskTier(score, tierConfig, null);
  const pct = `${(Math.min(1, Math.max(0, score)) * 100).toFixed(1)}%`;
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      {tier ? (
        <span
          className={`rounded border px-1.5 py-0.5 font-mono text-[10px] ${riskTierBadgeClass(tier)}`}
        >
          {riskTierLabel(tier)}
        </span>
      ) : (
        <span className="rounded border border-[var(--color-aegis-border)] bg-[#0d1117] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-aegis-muted)]">
          —
        </span>
      )}
      <span className="tabular-nums text-[#c8d4e0]">{pct}</span>
    </span>
  );
}

function RiskTierBadge({
  score,
  tierConfig,
  backendLevel,
}: {
  score: number;
  tierConfig: RiskTierConfig | null;
  backendLevel: string;
}) {
  const tier = resolveRiskTier(score, tierConfig, backendLevel);
  if (!tier) {
    return (
      <span className="inline-block rounded border border-[var(--color-aegis-border)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-aegis-muted)]">
        {backendLevel}
      </span>
    );
  }
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 font-mono text-[10px] ${riskTierBadgeClass(tier)}`}
    >
      {riskTierLabel(tier)}
    </span>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div className="rounded-lg border border-[var(--color-aegis-border)] bg-[#060810] p-4">
      <p className="font-data text-[11px] uppercase tracking-wide text-[#6b7c90]">
        {label}
      </p>
      <p
        className={`mt-1 font-display text-2xl font-bold tabular-nums ${
          accent ? "text-[#f87171]" : "text-[#e6edf3]"
        }`}
      >
        {value.toLocaleString()}
      </p>
    </div>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] p-5">
      <div className="mb-4 flex items-center gap-2">
        {icon}
        <h2 className="font-display text-sm font-semibold text-[#e6edf3]">
          {title}
        </h2>
      </div>
      {children}
    </div>
  );
}

