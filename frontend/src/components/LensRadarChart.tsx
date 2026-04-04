import { useMemo } from "react";
import Plot from "react-plotly.js";
import type { Data, Layout } from "plotly.js";

export interface LensRadarScores {
  behavioral: number;
  graph: number;
  entity: number;
  temporal: number;
  document: number;
  offramp: number;
}

export interface LensRadarChartProps {
  scores: LensRadarScores;
}

const LABELS = [
  "Behavioral",
  "Graph",
  "Entity",
  "Temporal",
  "Document",
  "Off-ramp",
] as const;

const PLOT_BG = "#111827";
const TEXT = "#f3f4f6";
const GRID = "#374151";

export default function LensRadarChart({ scores }: LensRadarChartProps) {
  const { data, layout } = useMemo(() => {
    const r = [
      scores.behavioral,
      scores.graph,
      scores.entity,
      scores.temporal,
      scores.document,
      scores.offramp,
    ];
    const theta = [...LABELS, LABELS[0]];
    const rClosed = [...r, r[0]];

    const trace: Partial<Data> = {
      type: "scatterpolar",
      r: rClosed,
      theta,
      fill: "toself",
      fillcolor: "rgba(59, 130, 246, 0.25)",
      line: { color: "#3b82f6", width: 2 },
      marker: { color: "#60a5fa", size: 6 },
    };

    const plotLayout: Partial<Layout> = {
      paper_bgcolor: PLOT_BG,
      plot_bgcolor: PLOT_BG,
      font: { color: TEXT, family: "system-ui, sans-serif", size: 11 },
      margin: { l: 48, r: 48, t: 32, b: 32 },
      polar: {
        bgcolor: PLOT_BG,
        radialaxis: {
          visible: true,
          range: [0, 1],
          gridcolor: GRID,
          linecolor: GRID,
          tickfont: { color: TEXT },
        },
        angularaxis: {
          tickfont: { color: TEXT },
          linecolor: GRID,
          gridcolor: GRID,
        },
      },
      showlegend: false,
    };

    return { data: [trace], layout: plotLayout };
  }, [scores]);

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-2 text-gray-100">
      <Plot
        data={data}
        layout={layout}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: 360 }}
        useResizeHandler
      />
    </div>
  );
}
