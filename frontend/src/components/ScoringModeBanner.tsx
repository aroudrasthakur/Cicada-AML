import { useScoringMode } from "@/contexts/useScoringMode";

type Variant = "card" | "strip";

export default function ScoringModeBanner({ variant = "card" }: { variant?: Variant }) {
  const { mode, metrics } = useScoringMode();

  const line = (
    <>
      <span className="text-[#9aa7b8]">
        {mode.replace(/_/g, " ")} active
      </span>
      <span className="text-[var(--color-aegis-border)]">·</span>
      <span>5 lens models + 185 heuristics</span>
      <span className="text-[var(--color-aegis-border)]">·</span>
      <span>
        Precision@50{" "}
        <span className="tabular-nums text-[#c8d4e0]">
          {metrics.precisionAt50.toFixed(2)}
        </span>
      </span>
      <span className="text-[var(--color-aegis-border)]">·</span>
      <span>
        Recall@50{" "}
        <span className="tabular-nums text-[#c8d4e0]">
          {metrics.recallAt50.toFixed(2)}
        </span>
      </span>
      <span className="text-[var(--color-aegis-border)]">·</span>
      <span>
        PR-AUC{" "}
        <span className="tabular-nums text-[#c8d4e0]">{metrics.prAuc.toFixed(3)}</span>
      </span>
    </>
  );

  if (variant === "strip") {
    return (
      <div className="border-b border-[var(--color-aegis-border)] bg-[#060810]/80 px-6 py-2.5 font-data text-[11px] leading-relaxed text-[#8b9cb3]">
        {line}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117] px-4 py-3 font-data text-xs text-[#8b9cb3]">
      <span className="text-[#e6edf3]">
        <span className="text-[var(--color-aegis-muted)]">scoring_mode</span>{" "}
        <span className="font-medium text-[#34d399]/90">{mode}</span>
      </span>
      <span className="h-4 w-px bg-[var(--color-aegis-border)]" aria-hidden />
      <span>
        Precision@50{" "}
        <span className="tabular-nums text-[#e6edf3]">
          {(metrics.precisionAt50 * 100).toFixed(1)}%
        </span>
      </span>
      <span>
        Recall@50{" "}
        <span className="tabular-nums text-[#e6edf3]">
          {(metrics.recallAt50 * 100).toFixed(1)}%
        </span>
      </span>
      <span>
        PR-AUC{" "}
        <span className="tabular-nums text-[#e6edf3]">
          {metrics.prAuc.toFixed(3)}
        </span>
      </span>
    </div>
  );
}
