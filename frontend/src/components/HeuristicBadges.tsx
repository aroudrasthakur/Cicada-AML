import { useMemo, useState } from "react";

export interface HeuristicBadgesProps {
  triggeredIds: number[];
  explanations: Record<string, string>;
  limit?: number;
}

type EnvGroup = "traditional" | "blockchain" | "hybrid" | "ai_enabled" | "unknown";

function environmentForId(id: number): EnvGroup {
  if (id >= 1 && id <= 90) return "traditional";
  if (id >= 91 && id <= 142) return "blockchain";
  if ((id >= 143 && id <= 155) || (id >= 176 && id <= 185)) return "hybrid";
  if (id >= 156 && id <= 175) return "ai_enabled";
  return "unknown";
}

function badgeClasses(env: EnvGroup): string {
  switch (env) {
    case "traditional":
      return "border-amber-700/80 bg-amber-950/40 text-amber-200";
    case "blockchain":
      return "border-blue-700/80 bg-blue-950/40 text-blue-200";
    case "hybrid":
      return "border-purple-700/80 bg-purple-950/40 text-purple-200";
    case "ai_enabled":
      return "border-red-700/80 bg-red-950/40 text-red-200";
    default:
      return "border-gray-700 bg-gray-800 text-gray-300";
  }
}

export default function HeuristicBadges({
  triggeredIds,
  explanations,
  limit = 8,
}: HeuristicBadgesProps) {
  const [expanded, setExpanded] = useState(false);

  const uniqueSorted = useMemo(() => {
    return [...new Set(triggeredIds)].sort((a, b) => a - b);
  }, [triggeredIds]);

  const visible = expanded ? uniqueSorted : uniqueSorted.slice(0, limit);
  const hiddenCount = Math.max(0, uniqueSorted.length - limit);

  if (uniqueSorted.length === 0) {
    return (
      <p className="text-sm text-gray-500">No heuristics triggered.</p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {visible.map((id) => {
          const key = String(id);
          const tip = explanations[key] ?? explanations[id] ?? `Heuristic ${id}`;
          const env = environmentForId(id);
          return (
            <span
              key={id}
              title={tip}
              className={`inline-flex cursor-default rounded-md border px-2 py-0.5 text-xs font-medium tabular-nums ${badgeClasses(env)}`}
            >
              H-{id}
            </span>
          );
        })}
      </div>
      {!expanded && hiddenCount > 0 && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="self-start text-xs font-medium text-blue-400 hover:text-blue-300"
        >
          Show more ({hiddenCount})
        </button>
      )}
    </div>
  );
}
