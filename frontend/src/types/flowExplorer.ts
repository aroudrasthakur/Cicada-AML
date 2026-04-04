/** Flow Explorer demo / visualization types */

export type FlowNodeType =
  | "source"
  | "layer"
  | "exit"
  | "feeder"
  | "collector"
  | "out";

export interface FlowExplorerNode {
  id: string;
  label: string;
  type: FlowNodeType;
  color: string;
  /** 0–1 fraction of canvas width */
  rx: number;
  /** 0–1 fraction of canvas height */
  ry: number;
  /** 0–1 risk for tooltip */
  risk: number;
}

export type FlowEdge = [fromId: string, toId: string, amountStr: string];

export interface FlowHeuristicChip {
  label: string;
  color: string;
  bg: string;
  border: string;
}

export interface FlowWalletRow {
  addr: string;
  type: string;
  badge: string;
  badgeColor: string;
}

export interface FlowTxRow {
  hash: string;
  route: string;
  amount: string;
}

export interface FlowCluster {
  key: "A" | "B" | "C";
  name: string;
  typology: string;
  typologyShort: string;
  risk: number;
  riskColor: string;
  riskLabel: string;
  wallets: number;
  tx: number;
  totalAmount: string;
  heuristics: FlowHeuristicChip[];
  wlist: FlowWalletRow[];
  txlist: FlowTxRow[];
  nodes: FlowExplorerNode[];
  edges: FlowEdge[];
}
