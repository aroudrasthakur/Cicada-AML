import type { CytoscapeElement } from "../types/graph";

interface ApiNode {
  id: string;
  risk_score?: number;
  label?: string;
  [key: string]: unknown;
}

interface ApiEdge {
  source: string;
  target: string;
  amount?: number;
  [key: string]: unknown;
}

interface ApiGraph {
  nodes: ApiNode[];
  edges: ApiEdge[];
}

export type { CytoscapeElement } from "../types/graph";

function riskToColor(score: number | undefined): string {
  if (score === undefined) return "#6b7280";
  if (score >= 0.75) return "#ef4444";
  if (score >= 0.5) return "#f97316";
  if (score >= 0.25) return "#eab308";
  return "#22c55e";
}

export function apiGraphToCytoscape(graph: ApiGraph): CytoscapeElement[] {
  const elements: CytoscapeElement[] = [];

  for (const node of graph.nodes) {
    const { id, label, risk_score, ...rest } = node;
    elements.push({
      data: {
        ...rest,
        id,
        label: label ?? id,
        color: riskToColor(risk_score),
      },
    });
  }

  for (const edge of graph.edges) {
    const { source, target, amount, ...rest } = edge;
    elements.push({
      data: {
        ...rest,
        source,
        target,
        weight: amount ?? 1,
      },
    });
  }

  return elements;
}
