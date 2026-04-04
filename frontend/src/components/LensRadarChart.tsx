import type { LensScores5 } from "@/types/dashboard";

export interface LensRadarChartProps {
  scores: LensScores5;
  size?: number;
}

const LABELS: { key: keyof LensScores5; label: string }[] = [
  { key: "behavioral", label: "Behavioral" },
  { key: "graph", label: "Graph" },
  { key: "entity", label: "Entity" },
  { key: "temporal", label: "Temporal" },
  { key: "offramp", label: "Off-ramp" },
];

/** Pentagonal radar: 5 axes, SVG only (no Plotly). */
export default function LensRadarChart({
  scores,
  size = 220,
}: LensRadarChartProps) {
  const cx = size / 2;
  const cy = size / 2 + 8;
  const rMax = size * 0.36;
  const n = 5;
  const points: string[] = [];
  const labelPos: { x: number; y: number; text: string }[] = [];

  for (let i = 0; i < n; i++) {
    const angle = (-Math.PI / 2 + (i * 2 * Math.PI) / n) as number;
    const v = Math.max(0, Math.min(1, scores[LABELS[i].key]));
    const r = rMax * v;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    points.push(`${x},${y}`);

    const lr = rMax + 22;
    labelPos.push({
      x: cx + lr * Math.cos(angle),
      y: cy + lr * Math.sin(angle),
      text: LABELS[i].label,
    });
  }

  const gridRings = [0.25, 0.5, 0.75, 1].map((t) => (
    <polygon
      key={t}
      fill="none"
      stroke="rgba(255,255,255,0.08)"
      strokeWidth={1}
      points={Array.from({ length: n }, (_, i) => {
        const angle = (-Math.PI / 2 + (i * 2 * Math.PI) / n) as number;
        const r = rMax * t;
        return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
      }).join(" ")}
    />
  ));

  const spokes = LABELS.map((_, i) => {
    const angle = (-Math.PI / 2 + (i * 2 * Math.PI) / n) as number;
    const x2 = cx + rMax * Math.cos(angle);
    const y2 = cy + rMax * Math.sin(angle);
    return (
      <line
        key={i}
        x1={cx}
        y1={cy}
        x2={x2}
        y2={y2}
        stroke="rgba(255,255,255,0.06)"
        strokeWidth={1}
      />
    );
  });

  return (
    <div className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] p-4">
      <p className="mb-2 font-data text-[10px] uppercase tracking-wider text-[var(--color-aegis-muted)]">
        Lens radar
      </p>
      <svg
        width={size}
        height={size + 16}
        viewBox={`0 0 ${size} ${size + 16}`}
        className="mx-auto block"
        role="img"
        aria-label="Five lens scores radar chart"
      >
        <defs>
          <filter id="radarGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {gridRings}
        {spokes}
        <polygon
          fill="rgba(0, 229, 160, 0.12)"
          stroke="var(--color-aegis-green)"
          strokeWidth={1.5}
          points={points.join(" ")}
          filter="url(#radarGlow)"
        />
        {labelPos.map((p) => (
          <text
            key={p.text}
            x={p.x}
            y={p.y}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-[#9aa7b8] font-data"
            style={{ fontSize: 9 }}
          >
            {p.text}
          </text>
        ))}
      </svg>
    </div>
  );
}
