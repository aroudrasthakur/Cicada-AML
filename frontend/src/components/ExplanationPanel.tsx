import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ExplanationDetail } from "../types/explanation";
import { formatNumber } from "../utils/formatters";

export interface ExplanationPanelProps {
  transactionId: string;
  explanation?: ExplanationDetail | null;
}

const LENS_KEYS = [
  { key: "behavioral", label: "Behavioral" },
  { key: "graph", label: "Graph" },
  { key: "entity", label: "Entity" },
  { key: "temporal", label: "Temporal" },
  { key: "document", label: "Document" },
  { key: "offramp", label: "Off-ramp" },
] as const;

function Badge({
  children,
  variant,
}: {
  children: ReactNode;
  variant: "blue" | "purple";
}) {
  const cls =
    variant === "blue"
      ? "border-blue-800 bg-blue-950/50 text-blue-200"
      : "border-purple-800 bg-purple-950/50 text-purple-200";
  return (
    <span
      className={`inline-flex rounded-md border px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {children}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value * 100));
  return (
    <div className="h-2 overflow-hidden rounded-full bg-gray-800">
      <div
        className="h-full rounded-full bg-blue-500"
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
    <section className="rounded-xl border border-gray-800 bg-gray-900 text-gray-100">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 border-b border-gray-800 px-4 py-3 text-left hover:bg-gray-800/40"
      >
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
            Explanation
          </p>
          <p className="mt-0.5 font-mono text-sm text-gray-200">
            {transactionId}
          </p>
        </div>
        {open ? (
          <ChevronDown className="h-5 w-5 shrink-0 text-gray-400" aria-hidden />
        ) : (
          <ChevronRight className="h-5 w-5 shrink-0 text-gray-400" aria-hidden />
        )}
      </button>

      {open && (
        <div className="space-y-6 p-4">
          {!explanation ? (
            <p className="text-sm text-gray-500">
              No explanation payload for this transaction.
            </p>
          ) : (
            <>
              {explanation.summary && (
                <div>
                  <h3 className="text-sm font-medium text-gray-300">Summary</h3>
                  <p className="mt-2 text-sm leading-relaxed text-gray-400">
                    {explanation.summary}
                  </p>
                </div>
              )}

              {explanation.heuristics && explanation.heuristics.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-300">
                    Triggered heuristics
                  </h3>
                  <ul className="mt-3 space-y-3">
                    {explanation.heuristics.map((h) => (
                      <li key={h.id} className="rounded-lg bg-gray-950/50 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm text-gray-200">
                            {h.label ?? `Heuristic #${h.id}`}
                          </span>
                          <span className="text-xs tabular-nums text-gray-500">
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
                <h3 className="text-sm font-medium text-gray-300">
                  Lens contributions
                </h3>
                <div className="mt-3 space-y-3">
                  {LENS_KEYS.map(({ key, label }) => {
                    const v = explanation.lenses?.[key];
                    return (
                      <div key={key}>
                        <div className="flex justify-between text-xs text-gray-400">
                          <span>{label}</span>
                          <span className="tabular-nums text-gray-500">
                            {v == null ? "—" : formatNumber(v, 2)}
                          </span>
                        </div>
                        <div className="mt-1">
                          {v == null ? (
                            <div className="h-2 rounded-full bg-gray-800" />
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
                  <Badge variant="blue">Pattern: {explanation.patternType}</Badge>
                )}
                {explanation.launderingStage && (
                  <Badge variant="purple">
                    Stage: {explanation.launderingStage}
                  </Badge>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
