import { useCallback, useEffect, useState } from "react";
import {
  GitBranch,
  Info,
  Loader2,
  AlertTriangle,
  ChevronDown,
} from "lucide-react";
import NetworkGraph from "@/components/NetworkGraph";
import { useRunContext } from "@/contexts/useRunContext";
import {
  fetchRunClusters,
  fetchClusterGraph,
  fetchClusterMembers,
  fetchRunSuspicious,
} from "@/api/runs";
import type { RunCluster, RunSuspiciousTx } from "@/types/run";
import type { CytoscapeElement } from "@/types/graph";

export default function FlowExplorerPage() {
  const { runs, activeRun, selectRun } = useRunContext();
  const completedRuns = runs.filter((r) => r.status === "completed");

  const [selectedRunId, setSelectedRunId] = useState<string | null>(
    activeRun?.status === "completed" ? activeRun.id : null,
  );
  const [clusters, setClusters] = useState<RunCluster[]>([]);
  const [activeClusterIdx, setActiveClusterIdx] = useState(0);
  const [elements, setElements] = useState<CytoscapeElement[]>([]);
  const [members, setMembers] = useState<{ wallet_address: string }[]>([]);
  const [suspiciousTxns, setSuspiciousTxns] = useState<RunSuspiciousTx[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    data: Record<string, unknown>;
  } | null>(null);

  // When selected run changes, load clusters
  useEffect(() => {
    if (!selectedRunId) {
      setClusters([]);
      setElements([]);
      setMembers([]);
      setSuspiciousTxns([]);
      return;
    }
    selectRun(selectedRunId);
    setLoading(true);
    Promise.all([
      fetchRunClusters(selectedRunId),
      fetchRunSuspicious(selectedRunId),
    ])
      .then(([cl, sus]) => {
        setClusters(cl);
        setSuspiciousTxns(sus);
        setActiveClusterIdx(0);
      })
      .catch(() => {
        setClusters([]);
        setSuspiciousTxns([]);
      })
      .finally(() => setLoading(false));
  }, [selectedRunId, selectRun]);

  // When active cluster changes, load its graph + members
  useEffect(() => {
    const cluster = clusters[activeClusterIdx];
    if (!selectedRunId || !cluster) {
      setElements([]);
      setMembers([]);
      return;
    }
    setLoading(true);
    Promise.all([
      fetchClusterGraph(selectedRunId, cluster.id),
      fetchClusterMembers(selectedRunId, cluster.id),
    ])
      .then(([snap, mem]) => {
        setElements((snap.elements ?? []) as unknown as CytoscapeElement[]);
        setMembers(mem);
      })
      .catch(() => {
        setElements([]);
        setMembers([]);
      })
      .finally(() => setLoading(false));
  }, [selectedRunId, clusters, activeClusterIdx]);

  // Set initial selectedRunId from latest completed run
  useEffect(() => {
    if (!selectedRunId && completedRuns.length > 0) {
      setSelectedRunId(completedRuns[0].id);
    }
  }, [completedRuns, selectedRunId]);

  const onNodeClick = useCallback((id: string) => {
    setSelected(id);
    setTooltip(null);
  }, []);

  const onNodeHover = useCallback(
    (id: string, pos: { x: number; y: number }, data: Record<string, unknown>) => {
      setTooltip({ x: pos.x, y: pos.y, data: { id, ...data } });
    },
    [],
  );

  const onNodeHoverOut = useCallback(() => {
    setTooltip(null);
  }, []);

  const activeCluster = clusters[activeClusterIdx] ?? null;
  const clusterSusTxns = activeCluster
    ? suspiciousTxns.filter((t) => t.cluster_id === activeCluster.id)
    : [];

  const hasSuspicious = suspiciousTxns.length > 0;

  return (
    <div className="flex min-h-[calc(100vh-8rem)] flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-[#e6edf3]">
            Flow Explorer
          </h1>
          <p className="font-data text-sm text-[var(--color-aegis-muted)]">
            Suspicious cluster graphs per pipeline run
          </p>
        </div>

        {/* Run selector */}
        <div className="relative">
          <select
            value={selectedRunId ?? ""}
            onChange={(e) => setSelectedRunId(e.target.value || null)}
            className="appearance-none rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117] py-2 pl-3 pr-8 font-data text-xs text-[#e6edf3] focus:border-[#34d399]/50 focus:outline-none"
          >
            <option value="">Select a run…</option>
            {completedRuns.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label || `Run ${r.id.slice(0, 8)}`} (
                {new Date(r.completed_at!).toLocaleDateString()})
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-[#6b7c90]" />
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-[#34d399]" />
        </div>
      )}

      {/* Empty state */}
      {!loading && (!selectedRunId || !hasSuspicious) && (
        <div className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] px-4 py-16 text-center">
          <GitBranch className="mx-auto mb-3 h-10 w-10 text-[var(--color-aegis-muted)]" />
          <p className="font-display font-medium text-[#c8d4e0]">
            {!selectedRunId
              ? "Select a completed run to explore"
              : "No suspicious transactions found in this run"}
          </p>
          <p className="mx-auto mt-2 max-w-sm text-sm text-[#9aa7b8]">
            Upload CSVs and run the pipeline. Suspicious clusters will appear
            here when detected.
          </p>
        </div>
      )}

      {/* Graph + side panel */}
      {!loading && hasSuspicious && clusters.length > 0 && (
        <>
          {/* Cluster tabs */}
          <div className="flex flex-wrap gap-1 rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117] p-1">
            {clusters.map((cl, i) => (
              <button
                key={cl.id}
                type="button"
                onClick={() => setActiveClusterIdx(i)}
                className={`rounded-md px-3 py-1.5 font-data text-xs transition-colors ${
                  i === activeClusterIdx
                    ? "bg-[#060810] text-[#34d399]"
                    : "text-[#9aa7b8] hover:text-[#e6edf3]"
                }`}
              >
                {cl.label || `Cluster ${i + 1}`}
                <span className="ml-1 text-[10px] text-[#6b7c90]">
                  ({cl.wallet_count}w / {cl.tx_count}tx)
                </span>
              </button>
            ))}
          </div>

          <div className="flex flex-1 flex-col gap-4 lg:flex-row lg:min-h-0">
            {/* Graph */}
            <div className="relative min-h-[480px] flex-1">
              <NetworkGraph
                elements={elements}
                onNodeClick={onNodeClick}
                onNodeHover={onNodeHover}
                onNodeHoverOut={onNodeHoverOut}
              />
              {/* Tooltip overlay */}
              {tooltip && (
                <div
                  className="pointer-events-none absolute z-50 max-w-xs rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117]/95 px-3 py-2 shadow-lg backdrop-blur-sm"
                  style={{ left: tooltip.x + 12, top: tooltip.y + 12 }}
                >
                  <dl className="space-y-1 font-data text-[11px] text-[#c8d4e0]">
                    {Object.entries(tooltip.data)
                      .filter(([k]) => !k.startsWith("_"))
                      .map(([k, v]) => (
                        <div key={k} className="flex gap-2">
                          <dt className="shrink-0 text-[#6b7c90]">{k}:</dt>
                          <dd className="truncate text-[#e6edf3]">
                            {String(v ?? "—")}
                          </dd>
                        </div>
                      ))}
                  </dl>
                </div>
              )}
            </div>

            {/* Side panel */}
            <aside className="w-full shrink-0 space-y-4 rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] p-5 lg:w-80">
              {/* Cluster info */}
              {activeCluster && (
                <div>
                  <div className="flex items-center gap-2">
                    <Info className="h-4 w-4 text-[var(--color-aegis-muted)]" />
                    <h2 className="font-display text-sm font-semibold text-[#e6edf3]">
                      {activeCluster.label}
                    </h2>
                  </div>
                  <dl className="mt-2 space-y-1 font-data text-xs text-[#c8d4e0]">
                    <div className="flex justify-between">
                      <dt className="text-[#6b7c90]">Typology</dt>
                      <dd>{activeCluster.typology ?? "—"}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-[#6b7c90]">Risk score</dt>
                      <dd>{((activeCluster.risk_score ?? 0) * 100).toFixed(0)}%</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-[#6b7c90]">Wallets</dt>
                      <dd>{activeCluster.wallet_count}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-[#6b7c90]">Transactions</dt>
                      <dd>{activeCluster.tx_count}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-[#6b7c90]">Total amount</dt>
                      <dd>${(activeCluster.total_amount ?? 0).toLocaleString()}</dd>
                    </div>
                  </dl>
                </div>
              )}

              {/* Members */}
              {members.length > 0 && (
                <div>
                  <h3 className="mb-2 font-display text-xs font-semibold uppercase tracking-wide text-[#6b7c90]">
                    Wallets in cluster
                  </h3>
                  <ul className="aegis-scroll max-h-40 space-y-1 overflow-y-auto pr-1">
                    {members.map((m) => (
                      <li
                        key={m.wallet_address}
                        className="truncate rounded bg-[#060810] px-2 py-1 font-mono text-[10px] text-[#c8d4e0]"
                      >
                        {m.wallet_address}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Suspicious txns in this cluster */}
              {clusterSusTxns.length > 0 && (
                <div>
                  <h3 className="mb-2 flex items-center gap-1 font-display text-xs font-semibold uppercase tracking-wide text-[#6b7c90]">
                    <AlertTriangle className="h-3 w-3 text-[#f87171]" />
                    Suspicious transactions
                  </h3>
                  <ul className="aegis-scroll max-h-48 space-y-1 overflow-y-auto pr-1">
                    {clusterSusTxns.map((t) => (
                      <li
                        key={t.id}
                        className="flex items-center justify-between rounded bg-[#060810] px-2 py-1"
                      >
                        <span className="truncate font-mono text-[10px] text-[#c8d4e0]">
                          {t.transaction_id.length > 20
                            ? `${t.transaction_id.slice(0, 20)}…`
                            : t.transaction_id}
                        </span>
                        <span className="ml-2 shrink-0 font-data text-[10px] tabular-nums text-[#f87171]">
                          {t.meta_score.toFixed(3)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Selected node */}
              {selected && (
                <div>
                  <h3 className="mb-1 font-display text-xs font-semibold uppercase tracking-wide text-[#6b7c90]">
                    Selected
                  </h3>
                  <p className="break-all font-mono text-[11px] text-[var(--color-aegis-green)]">
                    {selected}
                  </p>
                </div>
              )}
            </aside>
          </div>
        </>
      )}
    </div>
  );
}
