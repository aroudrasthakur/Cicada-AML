import { useEffect, useState } from "react";
import { Loader2, CheckCircle2, XCircle, Clock, Timer } from "lucide-react";
import { useRunContext } from "@/contexts/useRunContext";
import type { PipelineRun } from "@/types/run";

const LENS_LABELS = ["Behavioral", "Graph", "Temporal", "Off-ramp", "Entity"] as const;

function formatDurationMs(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return "—";
  const sec = Math.round(ms / 1000);
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}m ${s}s`;
}

function useElapsedMs(
  startedAt: string | null,
  endedAt: string | null,
  isRunning: boolean,
): number | null {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!isRunning) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [isRunning]);
  if (!startedAt) return null;
  const t0 = new Date(startedAt).getTime();
  const t1 = endedAt ? new Date(endedAt).getTime() : now;
  return t1 - t0;
}

function useRunElapsedMs(activeRun: PipelineRun | null) {
  return useElapsedMs(
    activeRun?.started_at ?? null,
    activeRun?.completed_at ?? null,
    activeRun?.status === "running",
  );
}

export default function RunStatusBar() {
  const { activeRun } = useRunContext();
  const runElapsedMs = useRunElapsedMs(activeRun);

  if (!activeRun) return null;

  const {
    status,
    progress_pct,
    label,
    error_message,
    started_at,
    completed_at,
    current_step,
    progress_log,
    scoring_tx_done,
    scoring_tx_total,
    lenses_completed,
    suspicious_tx_count,
    suspicious_cluster_count,
  } = activeRun;

  const lc = Math.min(5, Math.max(0, lenses_completed ?? 0));
  const logEntries = Array.isArray(progress_log) ? progress_log : [];

  if (status === "pending") {
    return (
      <Bar icon={<Clock className="h-4 w-4 text-[#facc15]" />} color="yellow">
        <span>Run {label ? `"${label}" ` : ""}queued</span>
      </Bar>
    );
  }

  if (status === "running") {
    return (
      <Bar
        icon={<Loader2 className="h-4 w-4 animate-spin text-[#60a5fa]" />}
        color="blue"
      >
        <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-start sm:gap-6">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <span className="font-medium text-[#e6edf3]">
              Pipeline running{label ? ` · ${label}` : ""}
            </span>
            <span className="rounded bg-[#1f2937] px-1.5 py-0.5 text-[#94a3b8]">
              {progress_pct}%
            </span>
            {runElapsedMs != null && (
              <span className="inline-flex items-center gap-1 text-[#94a3b8]">
                <Timer className="h-3 w-3" />
                {formatDurationMs(runElapsedMs)}
              </span>
            )}
            <div className="ml-1 h-1.5 w-28 overflow-hidden rounded-full bg-[#1e293b] sm:w-36">
              <div
                className="h-full rounded-full bg-[#60a5fa] transition-all duration-300"
                style={{ width: `${Math.min(100, progress_pct)}%` }}
              />
            </div>
          </div>
          <div className="min-w-0 flex-1 space-y-2 border-t border-[#60a5fa]/10 pt-2 sm:border-t-0 sm:pt-0 md:max-w-[55%]">
            {current_step ? (
              <p className="text-[11px] leading-snug text-[#93c5fd]">{current_step}</p>
            ) : null}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mr-1 text-[10px] uppercase tracking-wide text-[#64748b]">
                Lenses
              </span>
              {LENS_LABELS.map((name, i) => (
                <span
                  key={name}
                  className={`rounded px-1.5 py-0.5 text-[10px] ${
                    i < lc ? "bg-[#14532d] text-[#86efac]" : "bg-[#1e293b] text-[#64748b]"
                  }`}
                  title="Each transaction runs heuristics, then these five lenses, then the meta-learner."
                >
                  {i < lc ? "✓ " : ""}
                  {name}
                </span>
              ))}
            </div>
            {scoring_tx_total != null && scoring_tx_total > 0 && (
              <p className="text-[10px] text-[#64748b]">
                Scoring progress: {scoring_tx_done ?? 0} / {scoring_tx_total} transactions · all five
                lenses + meta applied per row
              </p>
            )}
            {logEntries.length > 0 && (
              <div className="max-h-24 overflow-y-auto rounded border border-[#1e293b] bg-[#0d1117]/90 p-2 font-mono text-[10px] leading-relaxed text-[#8b9cb3]">
                {logEntries.slice(-12).map((e, idx) => (
                  <div key={`${e.t}-${idx}`} className="border-b border-[#1e293b]/80 py-0.5 last:border-0">
                    <span className="text-[#475569]">
                      {e.t ? new Date(e.t).toLocaleTimeString() : ""}
                    </span>{" "}
                    {e.msg}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Bar>
    );
  }

  if (status === "completed") {
    const totalMs =
      started_at && completed_at
        ? new Date(completed_at).getTime() - new Date(started_at).getTime()
        : null;
    return (
      <Bar
        icon={<CheckCircle2 className="h-4 w-4 text-[#34d399]" />}
        color="green"
      >
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
          <span>
            Run{label ? ` "${label}"` : ""} completed — {suspicious_tx_count} suspicious,{" "}
            {suspicious_cluster_count} clusters
          </span>
          {totalMs != null && (
            <span className="text-[#86efac]/80">
              Total time {formatDurationMs(totalMs)}
            </span>
          )}
        </div>
      </Bar>
    );
  }

  if (status === "failed") {
    return (
      <Bar icon={<XCircle className="h-4 w-4 text-[#f87171]" />} color="red">
        <span>Run failed{error_message ? `: ${error_message}` : ""}</span>
      </Bar>
    );
  }

  return null;
}

function Bar({
  icon,
  color,
  children,
}: {
  icon: React.ReactNode;
  color: "yellow" | "blue" | "green" | "red";
  children: React.ReactNode;
}) {
  const borderMap = {
    yellow: "border-[#facc15]/20",
    blue: "border-[#60a5fa]/20",
    green: "border-[#34d399]/20",
    red: "border-[#f87171]/20",
  };
  return (
    <div
      className={`flex flex-col gap-2 border-b ${borderMap[color]} bg-[#0d1117]/80 px-4 py-3 font-data text-xs text-[#c8d4e0] sm:flex-row sm:items-start sm:gap-3`}
    >
      <div className="mt-0.5 shrink-0">{icon}</div>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
