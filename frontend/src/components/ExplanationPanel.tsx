import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ExplanationDetail } from "@/types/explanation";
import { formatNumber } from "@/utils/formatters";

export interface ExplanationPanelProps {
  transactionId: string;
  explanation?: ExplanationDetail | null;
}

const LENS_KEYS = [
  { key: "behavioral", label: "Behavioral" },
  { key: "graph", label: "Graph" },
  { key: "entity", label: "Entity" },
  { key: "temporal", label: "Temporal" },
  { key: "offramp", label: "Off-ramp" },
] as const;

function Badge({
  children,
  variant,
}: {
  children: ReactNode;
  variant: "green" | "purple";
}) {
  const cls =
    variant === "green"
      ? "border-[var(--color-aegis-green)]/40 bg-[#00e5a0]/10 text-[#6ee7b7]"
      : "border-[var(--color-aegis-purple)]/45 bg-[#7c5cfc]/15 text-[#c4b5fd]";
  return (
    <span
      className={`inline-flex rounded-md border px-2 py-0.5 font-data text-xs font-medium ${cls}`}
    >
      {children}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value * 100));
  return (
    <div className="h-2 overflow-hidden rounded-full bg-[#060810]">
      <div
        className="h-full rounded-full bg-[var(--color-aegis-green)]"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function ExplanationPanel({
  transactionId,
  explanation,
}: ExplanationPanelProps) {
  const [open, setOpen] = useState(true);

  return (
    <section className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] text-[#e6edf3]">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 border-b border-[var(--color-aegis-border)] px-4 py-3 text-left hover:bg-[#060810]/60"
      >
        <div>
          <p className="font-data text-[10px] font-medium uppercase tracking-wide text-[var(--color-aegis-muted)]">
            Explanation
          </p>
          <p className="mt-0.5 font-data text-sm text-[#e6edf3]">{transactionId}</p>
        </div>
        {open ? (
          <ChevronDown className="h-5 w-5 shrink-0 text-[var(--color-aegis-muted)]" aria-hidden />
        ) : (
          <ChevronRight className="h-5 w-5 shrink-0 text-[var(--color-aegis-muted)]" aria-hidden />
        )}
      </button>

      {open && (
        <div className="space-y-6 p-4">
          {!explanation ? (
            <p className="font-data text-sm text-[var(--color-aegis-muted)]">
              No explanation payload for this transaction.
            </p>
          ) : (
            <>
              {explanation.summary && (
                <div>
                  <h3 className="font-data text-sm font-medium text-[#c8d4e0]">Summary</h3>
                  <p className="mt-2 font-data text-sm leading-relaxed text-[#9aa7b8]">
                    {explanation.summary}
                  </p>
                </div>
              )}

              {explanation.shap && explanation.shap.length > 0 && (
                <div>
                  <h3 className="font-data text-sm font-medium text-[#c8d4e0]">
                    SHAP-style breakdown
                  </h3>
                  <ul className="mt-3 space-y-2">
                    {explanation.shap.map((s) => (
                      <li
                        key={s.name}
                        className="flex items-center justify-between gap-2 font-data text-xs"
                      >
                        <span className="text-[#9aa7b8]">{s.name}</span>
                        <span className="tabular-nums text-[#e6edf3]">
                          {formatNumber(s.value, 4)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {explanation.heuristics && explanation.heuristics.length > 0 && (
                <div>
                  <h3 className="font-data text-sm font-medium text-[#c8d4e0]">
                    Triggered heuristics
                  </h3>
                  <ul className="mt-3 space-y-3">
                    {explanation.heuristics.map((h) => (
                      <li
                        key={h.id}
                        className="rounded-lg border border-[var(--color-aegis-border)] bg-[#060810]/80 p-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-data text-sm text-[#e6edf3]">
                            {h.label ?? `Heuristic #${h.id}`}
                          </span>
                          <span className="font-data text-xs tabular-nums text-[var(--color-aegis-muted)]">
                            {formatNumber(h.confidence, 2)}
                          </span>
                        </div>
                        <div className="mt-2">
                          <ConfidenceBar value={h.confidence} />
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div>
                <h3 className="font-data text-sm font-medium text-[#c8d4e0]">
                  Lens contributions
                </h3>
                <div className="mt-3 space-y-3">
                  {LENS_KEYS.map(({ key, label }) => {
                    const v = explanation.lenses?.[key];
                    return (
                      <div key={key}>
                        <div className="flex justify-between font-data text-xs text-[#9aa7b8]">
                          <span>{label}</span>
                          <span className="tabular-nums text-[var(--color-aegis-muted)]">
                            {v == null ? "—" : formatNumber(v, 2)}
                          </span>
                        </div>
                        <div className="mt-1">
                          {v == null ? (
                            <div className="h-2 rounded-full bg-[#060810]" />
                          ) : (
                            <ConfidenceBar value={v} />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {explanation.patternType && (
                  <Badge variant="green">Pattern: {explanation.patternType}</Badge>
                )}
                {explanation.launderingStage && (
                  <Badge variant="purple">Stage: {explanation.launderingStage}</Badge>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
