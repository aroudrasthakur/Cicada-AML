import type { LensSignalScores } from "@/types/transaction";

const ORDER: { key: keyof LensSignalScores; title: string; color: string }[] = [
  { key: "behavioral", title: "Behavioral", color: "bg-[#00e5a0]" },
  { key: "graph", title: "Graph", color: "bg-[#7c5cfc]" },
  { key: "entity", title: "Entity", color: "bg-[#f59e0b]" },
  { key: "temporal", title: "Temporal", color: "bg-[#38bdf8]" },
  { key: "offramp", title: "Off-ramp", color: "bg-[#ff4d6d]" },
];

export function LensDots({ scores }: { scores: LensSignalScores }) {
  return (
    <div className="flex items-center gap-1" title="Lens signals">
      {ORDER.map(({ key, title, color }) => {
        const v = scores[key];
        const opacity = v >= 0.66 ? "" : v >= 0.33 ? "opacity-60" : "opacity-25";
        return (
          <span
            key={key}
            className={`h-2.5 w-2.5 rounded-full ${color} ${opacity}`}
            title={`${title}: ${(v * 100).toFixed(0)}%`}
          />
        );
      })}
    </div>
  );
}
