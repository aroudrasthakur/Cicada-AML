import { useMemo } from "react";
import Plot from "react-plotly.js";
import type { Data, Layout } from "plotly.js";
import type { ModelPerformanceMetric } from "@/types/dashboard";

export interface ModelPerformanceChartProps {
  metrics: ModelPerformanceMetric[];
}

/** Map FP/1k to 0–1 for shared axis (lower FP is better; invert for visual as “quality”) */
function fpNorm(fp: number): number {
  return Math.max(0, Math.min(1, 1 - fp / 40));
}

const LEGEND_ITEMS: { label: string; color: string; hint: string }[] = [
  { label: "PR-AUC", color: "#00e5a0", hint: "Precision–recall area" },
  { label: "Recall@50", color: "#7c5cfc", hint: "Recall at top 50%" },
  { label: "Precision@50", color: "#f59e0b", hint: "Precision at top 50%" },
  { label: "F1", color: "#38bdf8", hint: "F1 score" },
  {
    label: "FP/1k (inverted)",
    color: "#ff4d6d",
    hint: "False positives per 1k — higher bar = fewer FPs (see note below)",
  },
];

export default function ModelPerformanceChart({
  metrics,
}: ModelPerformanceChartProps) {
  const { data, layout } = useMemo(() => {
    const names = metrics.map((m) => m.name);
    const fpRaw = metrics.map((m) => m.fpPer1k);
    const traces: Data[] = [
      {
        type: "bar",
        name: "PR-AUC",
        orientation: "h",
        y: names,
        x: metrics.map((m) => m.prAuc),
        showlegend: false,
        marker: { color: "#00e5a0", line: { width: 0 } },
        hovertemplate:
          "%{y}<br><b>PR-AUC</b>: %{x:.3f}<extra></extra>",
      },
      {
        type: "bar",
        name: "Recall@50",
        orientation: "h",
        y: names,
        x: metrics.map((m) => m.recall50),
        showlegend: false,
        marker: { color: "#7c5cfc", line: { width: 0 } },
        hovertemplate:
          "%{y}<br><b>Recall@50</b>: %{x:.3f}<extra></extra>",
      },
      {
        type: "bar",
        name: "Precision@50",
        orientation: "h",
        y: names,
        x: metrics.map((m) => m.precision50),
        showlegend: false,
        marker: { color: "#f59e0b", line: { width: 0 } },
        hovertemplate:
          "%{y}<br><b>Precision@50</b>: %{x:.3f}<extra></extra>",
      },
      {
        type: "bar",
        name: "F1",
        orientation: "h",
        y: names,
        x: metrics.map((m) => m.f1),
        showlegend: false,
        marker: { color: "#38bdf8", line: { width: 0 } },
        hovertemplate: "%{y}<br><b>F1</b>: %{x:.3f}<extra></extra>",
      },
      {
        type: "bar",
        name: "FP/1k",
        orientation: "h",
        y: names,
        x: metrics.map((m) => fpNorm(m.fpPer1k)),
        showlegend: false,
        marker: { color: "#ff4d6d", line: { width: 0 } },
        customdata: fpRaw,
        hovertemplate:
          "%{y}<br>FP/1k (raw): %{customdata:.1f}<br>Normalized (1−fp/40): %{x:.3f}<extra></extra>",
      },
    ];

    const plotLayout: Partial<Layout> = {
      autosize: true,
      paper_bgcolor: "transparent",
      plot_bgcolor: "#060810",
      font: { color: "#c8d4e0", family: "DM Mono, ui-monospace, monospace", size: 11 },
      margin: { l: 92, r: 10, t: 6, b: 20 },
      barmode: "group",
      bargap: 0.18,
      bargroupgap: 0.04,
      hoverlabel: {
        bgcolor: "#0d1117",
        bordercolor: "rgba(255,255,255,0.12)",
        font: {
          family: "DM Mono, ui-monospace, monospace",
          size: 12,
          color: "#e6edf3",
        },
      },
      xaxis: {
        title: {
          text: "Score (0–1)",
          font: { size: 10, color: "#7d8a99" },
        },
        gridcolor: "rgba(255,255,255,0.07)",
        zerolinecolor: "rgba(255,255,255,0.1)",
        tickfont: { size: 10, color: "#7d8a99" },
        range: [0, 1],
        dtick: 0.2,
        showline: true,
        linecolor: "rgba(255,255,255,0.06)",
        mirror: false,
      },
      yaxis: {
        automargin: true,
        tickfont: { size: 11, color: "#e6edf3" },
        showline: false,
      },
    };

    return { data: traces, layout: plotLayout };
  }, [metrics]);

  return (
    <div className="max-w-full min-w-0 overflow-hidden rounded-2xl border border-[var(--color-aegis-border)] bg-gradient-to-b from-[#0d1117] to-[#060810] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]">
      <div className="border-b border-[var(--color-aegis-border)]/80 px-4 py-3 sm:px-5">
        <h3 className="font-display text-sm font-semibold tracking-tight text-[#e6edf3]">
          Model performance
        </h3>
        <p className="mt-0.5 max-w-2xl font-data text-[11px] leading-relaxed text-[var(--color-aegis-muted)]">
          Each lens vs the meta learner on a shared 0–1 axis.
        </p>
      </div>

      <div className="w-full min-w-0 max-w-full overflow-hidden px-1 pt-2 sm:px-3">
        <Plot
          data={data}
          layout={layout}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%", maxWidth: "100%", height: 240 }}
          useResizeHandler
        />
      </div>

      <div className="border-t border-[var(--color-aegis-border)]/60 bg-[#060810]/50 px-4 py-3 sm:px-5">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
          {LEGEND_ITEMS.map((item) => (
            <span
              key={item.label}
              className="inline-flex items-center gap-1.5"
              title={item.hint}
            >
              <span
                className="h-2 w-2 shrink-0 rounded-sm"
                style={{ backgroundColor: item.color }}
                aria-hidden
              />
              <span className="font-data text-[11px] text-[#c8d4e0]">
                {item.label}
              </span>
            </span>
          ))}
        </div>
        <p className="mt-2 font-data text-[11px] leading-relaxed text-[#5c6b7e]">
          FP/1k uses <span className="font-mono text-[#7d8a99]">1−fp/40</span> (longer = fewer FPs). Hover for raw values.
        </p>
      </div>
    </div>
  );
}
