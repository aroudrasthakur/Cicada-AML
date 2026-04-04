import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Flame } from "lucide-react";
import RiskSummaryCards from "@/components/RiskSummaryCards";
import TransactionTable from "@/components/TransactionTable";
import LensRadarChart from "@/components/LensRadarChart";
import TypologyHeatmap from "@/components/TypologyHeatmap";
import ModelPerformanceChart from "@/components/ModelPerformanceChart";
import type { TransactionQueueRow } from "@/types/transaction";
import type {
  LensScores5,
  LiveAlertItem,
  ModelPerformanceMetric,
  TriggeredHeuristicRow,
} from "@/types/dashboard";

function defaultLens(): NonNullable<TransactionQueueRow["lens_scores"]> {
  return {
    behavioral: 0.2,
    graph: 0.2,
    entity: 0.2,
    temporal: 0.2,
    offramp: 0.2,
  };
}

const MOCK_QUEUE: TransactionQueueRow[] = [
  {
    id: "1",
    display_ref: "TX-8821",
    transaction_id: "0x3fa2c1d9e8b7a4567890abcdef1234567890",
    tx_hash: null,
    sender_wallet: "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    receiver_wallet: "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
    amount: 124500,
    asset_type: "BTC",
    chain_id: "1",
    timestamp: new Date().toISOString(),
    fee: null,
    label: null,
    label_source: null,
    created_at: new Date().toISOString(),
    risk_score: 0.97,
    heuristics_count: 5,
    typology_tag: "Mixer Layering",
    lens_scores: {
      behavioral: 0.88,
      graph: 0.94,
      entity: 0.72,
      temporal: 0.81,
      offramp: 0.68,
    },
  },
  {
    id: "2",
    display_ref: "TX-8740",
    transaction_id: "0x2b4c6d8e0f1a234567890abcdef12345678",
    tx_hash: null,
    sender_wallet: "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    receiver_wallet: "0x1234567890123456789012345678901234567890",
    amount: 8900,
    asset_type: "ETH",
    chain_id: "1",
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    fee: null,
    label: null,
    label_source: null,
    created_at: new Date().toISOString(),
    risk_score: 0.83,
    heuristics_count: 4,
    typology_tag: "Structuring",
    lens_scores: {
      behavioral: 0.76,
      graph: 0.55,
      entity: 0.62,
      temporal: 0.7,
      offramp: 0.81,
    },
  },
  {
    id: "3",
    display_ref: "TX-8692",
    transaction_id: "0x9c1d8f2a3b4e5f678901234567890abcdef12",
    tx_hash: null,
    sender_wallet: "0xaaaabbbbccccddddeeeeffff000011112222",
    receiver_wallet: "0x33334444555566667777888899990000aaaa",
    amount: 42000,
    asset_type: "ETH",
    chain_id: "1",
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    fee: null,
    label: null,
    label_source: null,
    created_at: new Date().toISOString(),
    risk_score: 0.79,
    heuristics_count: 3,
    typology_tag: "Chain-Hop",
    lens_scores: {
      behavioral: 0.42,
      graph: 0.86,
      entity: 0.78,
      temporal: 0.55,
      offramp: 0.48,
    },
  },
  {
    id: "4",
    display_ref: "TX-8611",
    transaction_id: "0xdeadbeefcafe1234567890abcdef1234567890",
    tx_hash: null,
    sender_wallet: "0x111122223333444455556666777788889999",
    receiver_wallet: "0xaaaaaaaabbbbbbbbccccccccdddddddd",
    amount: 1500,
    asset_type: "ETH",
    chain_id: "1",
    timestamp: new Date(Date.now() - 10800000).toISOString(),
    fee: null,
    label: null,
    label_source: null,
    created_at: new Date().toISOString(),
    risk_score: 0.74,
    heuristics_count: 3,
    typology_tag: "NFT Wash Trade",
    lens_scores: {
      behavioral: 0.65,
      graph: 0.48,
      entity: 0.52,
      temporal: 0.72,
      offramp: 0.4,
    },
  },
  {
    id: "5",
    display_ref: "TX-8550",
    transaction_id: "0xfeedface0123456789abcdef0123456789ab",
    tx_hash: null,
    sender_wallet: "0x100020003000400050006000700080009000",
    receiver_wallet: "0x900080007000600050004000300020001000",
    amount: 250,
    asset_type: "ETH",
    chain_id: "1",
    timestamp: new Date(Date.now() - 14400000).toISOString(),
    fee: null,
    label: null,
    label_source: null,
    created_at: new Date().toISOString(),
    risk_score: 0.12,
    heuristics_count: 1,
    typology_tag: "Low-velocity test",
    lens_scores: {
      behavioral: 0.18,
      graph: 0.12,
      entity: 0.1,
      temporal: 0.14,
      offramp: 0.11,
    },
  },
];

const HEURISTICS_BY_TX: Record<string, TriggeredHeuristicRow[]> = {
  "1": [
    { id: "h1", typologyId: "T-014", name: "Rapid hop chain", confidence: 0.94, severity: "critical" },
    { id: "h2", typologyId: "T-022", name: "Round-amount clustering", confidence: 0.88, severity: "high" },
    { id: "h3", typologyId: "T-055", name: "Fan-in concentration", confidence: 0.76, severity: "high" },
  ],
  "2": [
    { id: "h4", typologyId: "T-031", name: "Threshold structuring", confidence: 0.82, severity: "high" },
    { id: "h5", typologyId: "T-067", name: "Temporal burst", confidence: 0.71, severity: "medium" },
  ],
  "3": [
    { id: "h6", typologyId: "T-091", name: "Cross-hop bridge", confidence: 0.79, severity: "high" },
    { id: "h7", typologyId: "T-104", name: "Wallet age mismatch", confidence: 0.64, severity: "medium" },
  ],
  "4": [
    { id: "h8", typologyId: "T-156", name: "NFT floor wash", confidence: 0.7, severity: "medium" },
  ],
  "5": [
    { id: "h9", typologyId: "T-002", name: "Benign pattern", confidence: 0.22, severity: "low" },
  ],
};

const ALERTS: LiveAlertItem[] = [
  { id: "a1", level: "critical", title: "Layering cluster #12", time: "2m ago" },
  { id: "a2", level: "high", title: "New mixer adjacency", time: "14m ago" },
];

const MODEL_METRICS: ModelPerformanceMetric[] = [
  { name: "Behavioral", prAuc: 0.84, recall50: 0.81, precision50: 0.79, f1: 0.8, fpPer1k: 12 },
  { name: "Graph", prAuc: 0.88, recall50: 0.85, precision50: 0.82, f1: 0.84, fpPer1k: 9 },
  { name: "Entity", prAuc: 0.79, recall50: 0.76, precision50: 0.74, f1: 0.75, fpPer1k: 15 },
  { name: "Temporal", prAuc: 0.81, recall50: 0.78, precision50: 0.77, f1: 0.78, fpPer1k: 11 },
  { name: "Off-ramp", prAuc: 0.83, recall50: 0.8, precision50: 0.78, f1: 0.79, fpPer1k: 10 },
  { name: "Meta", prAuc: 0.9, recall50: 0.91, precision50: 0.82, f1: 0.86, fpPer1k: 7 },
];

function severityColor(s: TriggeredHeuristicRow["severity"]) {
  if (s === "critical") return "text-[#f87171]";
  if (s === "high") return "text-[#fbbf24]";
  return "text-[#9aa7b8]";
}

function greetingForNow(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export default function DashboardPage() {
  const [selectedId, setSelectedId] = useState<string | null>(MOCK_QUEUE[0]?.id ?? null);
  const [queueFilter, setQueueFilter] = useState<"all" | "critical">("all");

  const filteredQueue = useMemo(() => {
    if (queueFilter === "critical") {
      return MOCK_QUEUE.filter((r) => (r.risk_score ?? 0) >= 0.75);
    }
    return MOCK_QUEUE;
  }, [queueFilter]);

  useEffect(() => {
    if (selectedId == null) return;
    const stillVisible = filteredQueue.some((r) => r.id === selectedId);
    if (!stillVisible && filteredQueue[0]) setSelectedId(filteredQueue[0].id);
  }, [filteredQueue, selectedId]);

  const selectedRow = useMemo(
    () => MOCK_QUEUE.find((r) => r.id === selectedId) ?? MOCK_QUEUE[0],
    [selectedId],
  );

  const radarScores: LensScores5 = useMemo(() => {
    const ls = selectedRow?.lens_scores ?? defaultLens();
    return {
      behavioral: ls.behavioral,
      graph: ls.graph,
      entity: ls.entity,
      temporal: ls.temporal,
      offramp: ls.offramp,
    };
  }, [selectedRow]);

  const heuristics = HEURISTICS_BY_TX[selectedRow?.id ?? ""] ?? HEURISTICS_BY_TX["1"] ?? [];

  const summary = useMemo(
    () => ({
      criticalAlerts: 24,
      txnsScored: 12841,
      networkCases: 7,
      heuristicsFired: 341,
      deltas: {
        criticalAlerts: 12,
        txnsScored: -1.2,
        networkCases: -3,
        heuristicsFired: 8.1,
      },
      trends: {
        criticalAlerts: "↑ this hour 3",
        txnsScored: "↓ vs 1.2% yesterday",
        networkCases: "↑ this week 2",
        heuristicsFired: "↑ vs 7-day avg 12%",
      },
    }),
    [],
  );

  const greeting = greetingForNow();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="font-display text-2xl font-semibold text-[#e6edf3]">
            {greeting}, Jamie.
          </p>
          <p className="mt-1 font-data text-sm text-[#9aa7b8]">
            Here&apos;s your risk overview for today —{" "}
            <span className="text-[#f87171]/95">24 alerts</span> need attention.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-6 font-mono text-[11px] uppercase tracking-wide text-[#7d8a99]">
          <div>
            <p className="text-[#f87171]/95">24 alerts</p>
          </div>
          <div>
            <p className="text-[#34d399]/95">0.91 recall</p>
          </div>
          <div>
            <p className="text-[#7dd3fc]/95">12.8k scored</p>
          </div>
        </div>
      </div>

      <RiskSummaryCards {...summary} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_320px]">
        <div className="min-w-0 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-display text-lg font-semibold text-[#e6edf3]">Risk queue</h2>
              <p className="mt-0.5 font-data text-xs text-[#9aa7b8]">Top 50 by meta-score</p>
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

          <TransactionTable

            transactions={filteredQueue}

            variant="queue"

            selectedId={selectedId}

            onSelect={(id) => setSelectedId(id)}

          />

        </div>



        <aside className="flex flex-col gap-4">

          <div className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117]/80 px-4 py-3">

            <p className="font-mono text-[10px] uppercase tracking-wide text-[#7d8a99]">

              Selected

            </p>

            <p className="mt-1 font-mono text-sm text-[#e6edf3]">

              {selectedRow?.display_ref ?? "—"}{" "}

              <span className="text-[#9aa7b8]">

                · {(selectedRow?.typology_tag ?? "").replace(/-/g, " ")}

              </span>

            </p>

          </div>

          <LensRadarChart key={selectedRow?.id ?? "none"} scores={radarScores} />

          <div className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] p-4">

            <h3 className="font-display text-sm font-semibold text-[#e6edf3]">

              Triggered heuristics

            </h3>

            <ul className="mt-3 space-y-2">

              {heuristics.map((h) => (

                <li

                  key={h.id}

                  className="flex flex-col gap-0.5 rounded border border-[var(--color-aegis-border)] bg-[#060810] px-3 py-2 font-data text-[11px]"

                >

                  <span className="text-[var(--color-aegis-muted)]">

                    {h.typologyId} · <span className={severityColor(h.severity)}>{h.name}</span>

                  </span>

                  <span className="tabular-nums text-[#c8d4e0]">

                    confidence {(h.confidence * 100).toFixed(1)}%

                  </span>

                </li>

              ))}

            </ul>

          </div>

          <div className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] p-4">

            <h3 className="font-display text-sm font-semibold text-[#e6edf3]">Live alerts</h3>

            <ul className="mt-3 space-y-2">

              {ALERTS.map((a) => (

                <li key={a.id} className="flex items-start gap-2 font-data text-[12px] text-[#c8d4e0]">

                  {a.level === "critical" ? (

                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[#f87171]" />

                  ) : (

                    <Flame className="mt-0.5 h-4 w-4 shrink-0 text-[#fbbf24]" />

                  )}

                  <div>

                    <p>{a.title}</p>

                    <p className="text-[10px] text-[var(--color-aegis-muted)]">{a.time}</p>

                  </div>

                </li>

              ))}

            </ul>

          </div>

        </aside>

      </div>



      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

        <TypologyHeatmap />

        <ModelPerformanceChart metrics={MODEL_METRICS} />

      </div>

    </div>

  );

}

