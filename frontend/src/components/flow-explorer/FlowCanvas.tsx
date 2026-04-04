import { useCallback, useEffect, useRef, useState } from "react";
import { Minus, Plus, RotateCcw } from "lucide-react";
import type {
  FlowCluster,
  FlowExplorerNode,
  FlowNodeType,
} from "@/types/flowExplorer";

/** Canvas / hover label for node role (internal type stays `source` for styling). */
function nodeTypeDisplayLabel(t: FlowNodeType): string {
  switch (t) {
    case "source":
      return "Entry";
    case "exit":
      return "Exit";
    case "layer":
      return "Layer";
    case "feeder":
      return "Feeder";
    case "collector":
      return "Collector";
    case "out":
      return "Out";
    default:
      return t;
  }
}

/** On-screen node radius (px); kept constant across zoom via world-space transform. */
const NODE_SCREEN_R = 14;
/** Extra hit padding (screen px) so selection is easier than the small disc alone. */
const NODE_HIT_PADDING_SCREEN = 8;
/** Screen px before a press on a node counts as a drag (avoids micro-jitter). */
const NODE_DRAG_THRESHOLD_PX = 6;
const ZOOM_MIN = 0.35;
const ZOOM_MAX = 2.75;
const ZOOM_STEP = 1.12;
const GRID_STEP = 56;
const GRID_LINE = "rgba(255,255,255,0.035)";
const MUTED = "#8b9cb3";
const ACCENT = "#34d399";
const LABEL = "#e6edf3";

type DragMap = Record<string, { dx: number; dy: number }>;

function neighborSet(
  selectedId: string | null,
  edges: FlowCluster["edges"],
  nodes: FlowExplorerNode[],
): Set<string> {
  if (!selectedId) return new Set(nodes.map((n) => n.id));
  const adj = new Map<string, Set<string>>();
  for (const [a, b] of edges) {
    if (!adj.has(a)) adj.set(a, new Set());
    if (!adj.has(b)) adj.set(b, new Set());
    adj.get(a)!.add(b);
    adj.get(b)!.add(a);
  }
  const out = new Set<string>([selectedId]);
  const stack = [selectedId];
  while (stack.length) {
    const u = stack.pop()!;
    for (const v of adj.get(u) ?? []) {
      if (!out.has(v)) {
        out.add(v);
        stack.push(v);
      }
    }
  }
  return out;
}

function edgeInClusterHighlight(
  selectedId: string | null,
  connected: Set<string>,
  a: string,
  b: string,
): boolean {
  if (!selectedId) return false;
  return connected.has(a) && connected.has(b);
}

function nodePos(
  n: FlowExplorerNode,
  drags: DragMap,
  w: number,
  h: number,
): { x: number; y: number } {
  const d = drags[n.id] ?? { dx: 0, dy: 0 };
  return { x: n.rx * w + d.dx, y: n.ry * h + d.dy };
}

function truncateLabel(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWorldW: number,
): string {
  if (ctx.measureText(text).width <= maxWorldW) return text;
  const ell = "…";
  let lo = 0;
  let hi = text.length;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    const t = text.slice(0, mid) + ell;
    if (ctx.measureText(t).width <= maxWorldW) lo = mid;
    else hi = mid - 1;
  }
  return text.slice(0, lo) + ell;
}

function hitNode(
  wx: number,
  wy: number,
  nodes: FlowExplorerNode[],
  drags: DragMap,
  cw: number,
  ch: number,
  scale: number,
): FlowExplorerNode | null {
  const rWorld = (NODE_SCREEN_R + NODE_HIT_PADDING_SCREEN) / scale;
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i]!;
    const { x, y } = nodePos(n, drags, cw, ch);
    const dx = wx - x;
    const dy = wy - y;
    if (dx * dx + dy * dy <= rWorld * rWorld) return n;
  }
  return null;
}

/** Zoom and pan so every node (labels + rough padding) fits in the viewport. */
function fitGraphToViewport(
  nodes: FlowExplorerNode[],
  cw: number,
  ch: number,
): { scale: number; offsetX: number; offsetY: number } {
  const pad = 40;
  const screenPadX = NODE_SCREEN_R + 42;
  const screenPadY = NODE_SCREEN_R + 58;
  if (nodes.length === 0 || cw < 48 || ch < 48) {
    return { scale: 1, offsetX: 0, offsetY: 0 };
  }
  const drags: DragMap = {};
  let minLx = Infinity;
  let maxLx = -Infinity;
  let minLy = Infinity;
  let maxLy = -Infinity;
  for (const n of nodes) {
    const { x, y } = nodePos(n, drags, cw, ch);
    minLx = Math.min(minLx, x);
    maxLx = Math.max(maxLx, x);
    minLy = Math.min(minLy, y);
    maxLy = Math.max(maxLy, y);
  }
  const bw = Math.max(maxLx - minLx, 72);
  const bh = Math.max(maxLy - minLy, 52);
  const availW = Math.max(cw - 2 * pad - 2 * screenPadX, 72);
  const availH = Math.max(ch - 2 * pad - 2 * screenPadY, 72);
  const s = Math.min(
    ZOOM_MAX,
    Math.max(ZOOM_MIN, Math.min(availW / bw, availH / bh)),
  );
  const cLx = (minLx + maxLx) / 2;
  const cLy = (minLy + maxLy) / 2;
  return {
    scale: s,
    offsetX: cw / 2 - s * cLx,
    offsetY: ch / 2 - s * cLy,
  };
}

export type FlowHoverPayload = {
  id: string;
  label: string;
  type: string;
  risk: number;
  clientX: number;
  clientY: number;
};

const LEGEND: { label: string; color: string }[] = [
  { label: "Entry", color: "#EF4444" },
  { label: "Layer", color: "#34d399" },
  { label: "Exit", color: "#8B5CF6" },
];

export function FlowCanvas({
  cluster,
  selectedNodeId,
  onSelectNode,
  onHover,
  walletFocusAddr,
  typologyBadge,
}: {
  cluster: FlowCluster;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  onHover: (p: FlowHoverPayload | null) => void;
  walletFocusAddr: string | null;
  typologyBadge: string;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState({ w: 400, h: 300 });
  const [offsetX, setOffsetX] = useState(0);
  const [offsetY, setOffsetY] = useState(0);
  const [scale, setScale] = useState(1);
  const [drags, setDrags] = useState<DragMap>({});
  const [cursor, setCursor] = useState<"default" | "pointer" | "grab" | "grabbing">(
    "grab",
  );
  const flowTRef = useRef(0);
  const rafRef = useRef(0);
  const scaleRef = useRef(1);
  const offsetRef = useRef({ x: 0, y: 0 });
  scaleRef.current = scale;
  offsetRef.current = { x: offsetX, y: offsetY };

  const dragRef = useRef<
    | {
        kind: "node";
        id: string;
        startWx: number;
        startWy: number;
        startDrag: { dx: number; dy: number };
      }
    | {
        kind: "node_pending";
        id: string;
        pressMx: number;
        pressMy: number;
        startDrag: { dx: number; dy: number };
      }
    | { kind: "pan"; ox: number; oy: number; startMx: number; startMy: number }
    | null
  >(null);

  const clusterKey = cluster.key;

  useEffect(() => {
    setDrags({});
    onSelectNode(null);
  }, [clusterKey, onSelectNode]);

  useEffect(() => {
    const fit = fitGraphToViewport(cluster.nodes, size.w, size.h);
    setScale(fit.scale);
    setOffsetX(fit.offsetX);
    setOffsetY(fit.offsetY);
  }, [clusterKey, cluster.nodes, size.h, size.w]);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (!cr) return;
      const w = Math.max(1, Math.floor(cr.width));
      const h = Math.max(1, Math.floor(cr.height));
      setSize((prev) => (prev.w === w && prev.h === h ? prev : { w, h }));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const { w: cw, h: ch } = size;
    const dpr = Math.min(window.devicePixelRatio ?? 1, 2);
    canvas.width = Math.floor(cw * dpr);
    canvas.height = Math.floor(ch * dpr);
    canvas.style.width = `${cw}px`;
    canvas.style.height = `${ch}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cw, ch);

    const s = scale;
    const ox = offsetX;
    const oy = offsetY;

    const connected = neighborSet(selectedNodeId, cluster.edges, cluster.nodes);

    ctx.save();
    ctx.translate(ox, oy);
    ctx.scale(s, s);

    const vx0 = (-ox) / s;
    const vy0 = (-oy) / s;
    const vx1 = (cw - ox) / s;
    const vy1 = (ch - oy) / s;
    const gx0 = Math.floor(vx0 / GRID_STEP) * GRID_STEP;
    const gy0 = Math.floor(vy0 / GRID_STEP) * GRID_STEP;

    ctx.strokeStyle = GRID_LINE;
    ctx.lineWidth = 1 / s;
    for (let x = gx0; x <= vx1 + GRID_STEP; x += GRID_STEP) {
      ctx.beginPath();
      ctx.moveTo(x, vy0);
      ctx.lineTo(x, vy1);
      ctx.stroke();
    }
    for (let y = gy0; y <= vy1 + GRID_STEP; y += GRID_STEP) {
      ctx.beginPath();
      ctx.moveTo(vx0, y);
      ctx.lineTo(vx1, y);
      ctx.stroke();
    }

    const rWorld = NODE_SCREEN_R / s;
    const nodeById = new Map(cluster.nodes.map((n) => [n.id, n] as const));

    const shortenEdge = (x1: number, y1: number, x2: number, y2: number) => {
      const dx = x2 - x1;
      const dy = y2 - y1;
      const len = Math.hypot(dx, dy) || 1;
      const ux = dx / len;
      const uy = dy / len;
      return {
        x1: x1 + ux * rWorld,
        y1: y1 + uy * rWorld,
        x2: x2 - ux * rWorld,
        y2: y2 - uy * rWorld,
        ux,
        uy,
      };
    };

    const flowT = flowTRef.current;

    cluster.edges.forEach(([fromId, toId, amountStr], ei) => {
      const na = nodeById.get(fromId);
      const nb = nodeById.get(toId);
      if (!na || !nb) return;
      const pa = nodePos(na, drags, cw, ch);
      const pb = nodePos(nb, drags, cw, ch);
      const se = shortenEdge(pa.x, pa.y, pb.x, pb.y);
      const hi = edgeInClusterHighlight(
        selectedNodeId,
        connected,
        fromId,
        toId,
      );

      ctx.strokeStyle = hi ? ACCENT : "rgba(139, 156, 179, 0.45)";
      ctx.lineWidth = (hi ? 2.25 : 1.25) / s;
      if (hi) ctx.setLineDash([]);
      else ctx.setLineDash([10 / s, 8 / s]);

      ctx.beginPath();
      ctx.moveTo(se.x1, se.y1);
      ctx.lineTo(se.x2, se.y2);
      ctx.stroke();
      ctx.setLineDash([]);

      const ah = 7 / s;
      const aw = 5 / s;
      ctx.fillStyle = hi ? ACCENT : "rgba(139, 156, 179, 0.65)";
      ctx.beginPath();
      ctx.moveTo(se.x2, se.y2);
      ctx.lineTo(
        se.x2 - se.ux * ah - se.uy * aw,
        se.y2 - se.uy * ah + se.ux * aw,
      );
      ctx.lineTo(
        se.x2 - se.ux * ah + se.uy * aw,
        se.y2 - se.uy * ah - se.ux * aw,
      );
      ctx.closePath();
      ctx.fill();

      const t = (flowT + ei * 0.19) % 1;
      const dotX = se.x1 + (se.x2 - se.x1) * t;
      const dotY = se.y1 + (se.y2 - se.y1) * t;
      ctx.fillStyle = ACCENT;
      ctx.beginPath();
      ctx.arc(dotX, dotY, 2.5 / s, 0, Math.PI * 2);
      ctx.fill();

      const midX = (se.x1 + se.x2) / 2;
      const midY = (se.y1 + se.y2) / 2;
      ctx.font = `${8 / s}px ui-monospace, monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      ctx.fillStyle = hi ? LABEL : "rgba(139, 156, 179, 0.7)";
      ctx.fillText(amountStr, midX, midY - 4 / s);
    });

    for (const n of cluster.nodes) {
      const { x, y } = nodePos(n, drags, cw, ch);
      const dim = !connected.has(n.id) ? 0.25 : 1;
      const focus =
        walletFocusAddr != null && n.label === walletFocusAddr ? 1 : 0;

      ctx.globalAlpha = dim;
      ctx.strokeStyle = n.color;
      ctx.lineWidth = (focus ? 2.2 : 1.15) / s;
      ctx.beginPath();
      ctx.arc(x, y, rWorld, 0, Math.PI * 2);
      ctx.fillStyle = "transparent";
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = n.color;
      ctx.beginPath();
      ctx.arc(x, y, 2.5 / s, 0, Math.PI * 2);
      ctx.fill();

      const typePad = 3 / s;
      const labelPad = 2 / s;
      const maxLabelW = 88 / s;

      ctx.font = `${6.5 / s}px ui-sans-serif, system-ui, sans-serif`;
      ctx.fillStyle = MUTED;
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      const typeStr = nodeTypeDisplayLabel(n.type);
      const typeCap =
        typeStr.length > 10 ? `${typeStr.slice(0, 9)}…` : typeStr;
      ctx.fillText(typeCap, x, y - rWorld - typePad);

      ctx.font = `${7.75 / s}px ui-monospace, monospace`;
      ctx.fillStyle = LABEL;
      ctx.textBaseline = "top";
      const shortLabel = truncateLabel(ctx, n.label, maxLabelW);
      ctx.fillText(shortLabel, x, y + rWorld + labelPad);

      ctx.globalAlpha = 1;
    }

    ctx.restore();
  }, [cluster, drags, offsetX, offsetY, scale, selectedNodeId, size, walletFocusAddr]);

  useEffect(() => {
    const tick = () => {
      flowTRef.current = (flowTRef.current + 0.0065) % 1;
      draw();
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [draw]);

  const screenToWorld = useCallback((mx: number, my: number) => {
    const sc = scaleRef.current;
    const { x, y } = offsetRef.current;
    return { wx: (mx - x) / sc, wy: (my - y) / sc };
  }, []);

  const onWheel = useCallback(
    (e: React.WheelEvent<HTMLCanvasElement>) => {
      e.preventDefault();
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const factor = e.deltaY > 0 ? 1 / ZOOM_STEP : ZOOM_STEP;
      const newScale = Math.min(
        ZOOM_MAX,
        Math.max(ZOOM_MIN, scaleRef.current * factor),
      );
      const { wx, wy } = screenToWorld(mx, my);
      setScale(newScale);
      setOffsetX(mx - wx * newScale);
      setOffsetY(my - wy * newScale);
    },
    [screenToWorld],
  );

  const onMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const { wx, wy } = screenToWorld(mx, my);
      const hit = hitNode(wx, wy, cluster.nodes, drags, size.w, size.h, scale);
      if (hit) {
        const cur = drags[hit.id] ?? { dx: 0, dy: 0 };
        dragRef.current = {
          kind: "node_pending",
          id: hit.id,
          pressMx: mx,
          pressMy: my,
          startDrag: { ...cur },
        };
        setCursor("pointer");
        onSelectNode(hit.id);
      } else {
        dragRef.current = {
          kind: "pan",
          ox: offsetX,
          oy: offsetY,
          startMx: mx,
          startMy: my,
        };
        setCursor("grabbing");
        onSelectNode(null);
      }
    },
    [
      cluster.nodes,
      drags,
      offsetX,
      offsetY,
      onSelectNode,
      scale,
      screenToWorld,
      size.h,
      size.w,
    ],
  );

  const onMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const { wx, wy } = screenToWorld(mx, my);
      let d = dragRef.current;

      if (d?.kind === "pan") {
        setOffsetX(d.ox + (mx - d.startMx));
        setOffsetY(d.oy + (my - d.startMy));
        return;
      }
      if (d?.kind === "node_pending") {
        const moved = Math.hypot(mx - d.pressMx, my - d.pressMy);
        if (moved >= NODE_DRAG_THRESHOLD_PX) {
          dragRef.current = {
            kind: "node",
            id: d.id,
            startWx: wx,
            startWy: wy,
            startDrag: { ...d.startDrag },
          };
          setCursor("grabbing");
          d = dragRef.current;
        }
      }
      if (d?.kind === "node") {
        const dwx = wx - d.startWx;
        const dwy = wy - d.startWy;
        setDrags((prev) => ({
          ...prev,
          [d.id]: {
            dx: d.startDrag.dx + dwx,
            dy: d.startDrag.dy + dwy,
          },
        }));
        return;
      }

      const hit = hitNode(wx, wy, cluster.nodes, drags, size.w, size.h, scale);
      if (hit) {
        setCursor("pointer");
        onHover({
          id: hit.id,
          label: hit.label,
          type: nodeTypeDisplayLabel(hit.type),
          risk: hit.risk,
          clientX: e.clientX,
          clientY: e.clientY,
        });
      } else {
        setCursor("grab");
        onHover(null);
      }
    },
    [
      cluster.nodes,
      drags,
      onHover,
      scale,
      screenToWorld,
      size.h,
      size.w,
    ],
  );

  const onMouseUp = useCallback(() => {
    dragRef.current = null;
    setCursor("grab");
  }, []);

  const onMouseLeave = useCallback(() => {
    dragRef.current = null;
    setCursor("grab");
    onHover(null);
  }, [onHover]);

  const zoomBy = useCallback(
    (dir: 1 | -1) => {
      const cw = size.w;
      const ch = size.h;
      const mx = cw / 2;
      const my = ch / 2;
      const factor = dir > 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
      const newScale = Math.min(
        ZOOM_MAX,
        Math.max(ZOOM_MIN, scaleRef.current * factor),
      );
      const { wx, wy } = screenToWorld(mx, my);
      setScale(newScale);
      setOffsetX(mx - wx * newScale);
      setOffsetY(my - wy * newScale);
    },
    [screenToWorld, size.h, size.w],
  );

  const resetView = useCallback(() => {
    const base: DragMap = {};
    for (const n of cluster.nodes) base[n.id] = { dx: 0, dy: 0 };
    setDrags(base);
    const fit = fitGraphToViewport(cluster.nodes, size.w, size.h);
    setScale(fit.scale);
    setOffsetX(fit.offsetX);
    setOffsetY(fit.offsetY);
  }, [cluster.nodes, size.h, size.w]);

  return (
    <div
      ref={wrapRef}
      className="relative min-h-0 min-w-0 w-full max-w-full flex-1 overflow-hidden bg-[#060810]"
    >
      <canvas
        ref={canvasRef}
        className="block h-full w-full"
        style={{ cursor }}
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseLeave}
      />

      <div className="pointer-events-none absolute left-2 right-2 top-2 z-10 flex min-w-0 flex-wrap items-center justify-between gap-2 sm:left-3 sm:right-3 sm:top-3">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5 sm:gap-2">
          <div className="max-w-[min(260px,45%)] shrink-0 rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-1.5">
            <p className="font-data text-[11px] text-[#6ee7b7]">{typologyBadge}</p>
            <p className="mt-0.5 font-data text-[13px] tabular-nums text-[#e6edf3]">
              Risk {(cluster.risk * 100).toFixed(0)}%
            </p>
          </div>
          <div className="rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117]/95 px-3 py-1.5">
            <ul className="flex flex-wrap items-center gap-x-4 gap-y-1">
              {LEGEND.map((item) => (
                <li key={item.label} className="flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="font-data text-[11px] text-[#e6edf3]">{item.label}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="pointer-events-auto flex shrink-0 items-center gap-1">
        <button
          type="button"
          aria-label="Zoom in"
          onClick={() => zoomBy(1)}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] text-[#e6edf3] hover:border-[#34d399]/35"
        >
          <Plus className="h-4 w-4" aria-hidden />
        </button>
        <button
          type="button"
          aria-label="Zoom out"
          onClick={() => zoomBy(-1)}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] text-[#e6edf3] hover:border-[#34d399]/35"
        >
          <Minus className="h-4 w-4" aria-hidden />
        </button>
        <button
          type="button"
          aria-label="Reset pan and zoom"
          onClick={resetView}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] text-[#e6edf3] hover:border-[#34d399]/35"
        >
          <RotateCcw className="h-4 w-4" aria-hidden />
        </button>
        </div>
      </div>
    </div>
  );
}
