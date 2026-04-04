import { useEffect, useMemo, useRef, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import type {
  Core,
  ElementDefinition,
  EventObject,
  StylesheetJsonBlock,
} from "cytoscape";
import type { CytoscapeElement } from "../types/graph";

export interface NetworkGraphProps {
  elements: CytoscapeElement[];
  onNodeClick?: (id: string) => void;
}

const DARK_BG = "#111827";

export default function NetworkGraph({
  elements,
  onNodeClick,
}: NetworkGraphProps) {
  const [cyInstance, setCyInstance] = useState<Core | null>(null);
  const onNodeClickRef = useRef(onNodeClick);
  onNodeClickRef.current = onNodeClick;

  const stylesheet = useMemo<StylesheetJsonBlock[]>(
    () => [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "background-color": "data(color)",
          color: "#e5e7eb",
          "text-outline-color": DARK_BG,
          "text-outline-width": 2,
          "font-size": 10,
          width: 28,
          height: 28,
        },
      },
      {
        selector: "edge",
        style: {
          width: "mapData(weight, 0, 1000000, 1, 12)",
          "line-color": "#4b5563",
          "target-arrow-color": "#4b5563",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          opacity: 0.85,
        },
      },
    ],
    [],
  );

  const layout = useMemo(
    () => ({
      name: "cose",
      animate: true,
      padding: 24,
      nodeRepulsion: 8000,
      idealEdgeLength: 100,
      componentSpacing: 60,
    }),
    [],
  );

  useEffect(() => {
    if (!cyInstance) return;
    const handler = (evt: EventObject) => {
      onNodeClickRef.current?.(evt.target.id());
    };
    cyInstance.on("tap", "node", handler);
    return () => {
      cyInstance.removeListener("tap", "node", handler);
    };
  }, [cyInstance]);

  return (
    <div
      className="h-full min-h-[420px] w-full overflow-hidden rounded-xl border border-gray-800 bg-gray-900"
      style={{ backgroundColor: DARK_BG }}
    >
      <CytoscapeComponent
        elements={CytoscapeComponent.normalizeElements(
          elements as ElementDefinition[],
        )}
        stylesheet={stylesheet}
        layout={layout}
        style={{ width: "100%", height: "100%", minHeight: 420 }}
        cy={(cy) => setCyInstance(cy)}
        wheelSensitivity={0.2}
      />
    </div>
  );
}
