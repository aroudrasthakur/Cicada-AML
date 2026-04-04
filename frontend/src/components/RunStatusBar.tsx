import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import { useRunContext } from "@/contexts/useRunContext";

export default function RunStatusBar() {
  const { activeRun } = useRunContext();

  if (!activeRun) return null;

  const { status, progress_pct, label, error_message } = activeRun;

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
        <span>
          Pipeline running{label ? ` "${label}"` : ""} — {progress_pct}%
        </span>
        <div className="ml-3 h-1.5 w-32 overflow-hidden rounded-full bg-[#1e293b]">
          <div
            className="h-full rounded-full bg-[#60a5fa] transition-all"
            style={{ width: `${progress_pct}%` }}
          />
        </div>
      </Bar>
    );
  }

  if (status === "completed") {
    return (
      <Bar
        icon={<CheckCircle2 className="h-4 w-4 text-[#34d399]" />}
        color="green"
      >
        <span>
          Run{label ? ` "${label}"` : ""} completed —{" "}
          {activeRun.suspicious_tx_count} suspicious, {activeRun.suspicious_cluster_count} clusters
        </span>
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
      className={`flex items-center gap-2 border-b ${borderMap[color]} bg-[#0d1117]/80 px-6 py-2 font-data text-xs text-[#c8d4e0]`}
    >
      {icon}
      {children}
    </div>
  );
}
