"""Build train_features.csv and graph artifacts from the Elliptic Bitcoin dataset (local CSVs).

Expected inputs under ``--input`` (default ``data/external``):

- ``elliptic_txs_features.csv`` — feature matrix (no header)
- ``elliptic_txs_classes.csv`` — txId, class (1=illicit, 2=licit, unknown)
- ``elliptic_txs_edgelist.csv`` — directed edges between transaction ids

Run from the backend directory, e.g.:

  python -m scripts.prepare_features --input ../data/external --output ../data/processed
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

from app.ml.graph_features import compute_graph_features
from app.ml.transaction_features import compute_transaction_features
from app.services.graph_service import build_wallet_graph
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _load_elliptic(input_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    features_path = input_dir / "elliptic_txs_features.csv"
    classes_path = input_dir / "elliptic_txs_classes.csv"
    edges_path = input_dir / "elliptic_txs_edgelist.csv"
    for p in (features_path, classes_path, edges_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing Elliptic file: {p}")

    features_df = pd.read_csv(features_path, header=None)
    classes_df = pd.read_csv(classes_path)
    edges_df = pd.read_csv(edges_path)
    return features_df, classes_df, edges_df


def _amount_proxy(features_df: pd.DataFrame) -> pd.Series:
    """Use aggregate local-feature magnitude as a synthetic amount (Elliptic has no raw BTC amount)."""
    local = features_df.iloc[:, 2:95].to_numpy(dtype=np.float64)
    return np.abs(local).sum(axis=1)


def _light_node_features(G: nx.DiGraph) -> dict[str, dict[str, Any]]:
    """Degrees, volumes, and balance only—no global centrality (betweenness/pagerank are too slow on full Elliptic)."""
    result: dict[str, dict[str, Any]] = {}
    for n in G.nodes():
        w_in = 0.0
        w_out = 0.0
        for _, _, data in G.in_edges(n, data=True):
            w_in += float(data.get("amount", 0) or 0)
        for _, _, data in G.out_edges(n, data=True):
            w_out += float(data.get("amount", 0) or 0)
        ideg = int(G.in_degree(n))
        odeg = int(G.out_degree(n))
        denom = w_in + w_out
        bal = (w_in - w_out) / denom if denom > 0 else 0.0
        vol = w_in + w_out
        result[str(n)] = {
            "in_degree": ideg,
            "out_degree": odeg,
            "weighted_in": w_in,
            "weighted_out": w_out,
            "total_volume": vol,
            "balance_ratio": bal,
            "betweenness_centrality": 0.0,
            "pagerank": 0.0,
            "clustering_coefficient": 0.0,
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare training features from Elliptic CSVs")
    parser.add_argument(
        "--input",
        default="data/external",
        help="Directory with elliptic_txs_features.csv, elliptic_txs_classes.csv, elliptic_txs_edgelist.csv",
    )
    parser.add_argument(
        "--output",
        default="data/processed",
        help="Directory to write train_features.csv, edges.csv, node_labels.csv",
    )
    args = parser.parse_args()
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading Elliptic from %s", input_dir.resolve())
    features_df, classes_df, edges_df = _load_elliptic(input_dir)

    classes_df.columns = ["txId", "class"]
    class_map = dict(zip(classes_df["txId"].astype(str), classes_df["class"].astype(str)))
    edges_df.columns = ["txId1", "txId2"]

    node_ids = features_df.iloc[:, 0].astype(str)
    time_steps = features_df.iloc[:, 1].astype(np.int64)
    amounts = _amount_proxy(features_df)

    amount_by_tx = dict(zip(node_ids, amounts))
    time_by_tx = dict(zip(node_ids, time_steps))

    base_ts = pd.Timestamp("2019-01-01", tz="UTC")

    def _ts_for(tid: str) -> pd.Timestamp:
        return base_ts + pd.to_timedelta(int(time_by_tx.get(tid, 0)), unit="h")

    # Full graph: one transaction record per edge (flow between tx nodes)
    edge_records: list[dict] = []
    for _, row in edges_df.iterrows():
        u, v = str(row["txId1"]), str(row["txId2"])
        if u == v:
            continue
        amt_u = float(amount_by_tx.get(u, 0.0))
        edge_records.append(
            {
                "transaction_id": f"e_{u}_{v}",
                "sender_wallet": u,
                "receiver_wallet": v,
                "amount": max(amt_u, 1e-8),
                "timestamp": _ts_for(u),
            }
        )

    if not edge_records:
        raise RuntimeError("No valid edges after filtering; check elliptic_txs_edgelist.csv")

    G = build_wallet_graph(edge_records)
    logger.info("Computing per-node degrees/volumes (skipping global centrality for speed)")
    node_feats = _light_node_features(G)
    graph_feat = compute_graph_features(G, node_feats)
    graph_feat.index = graph_feat.index.astype(str)

    br_series = pd.Series(
        {str(k): float(v.get("balance_ratio", 0.0) or 0.0) for k, v in node_feats.items()},
        dtype=np.float64,
    )

    # Adjacency for choosing a representative edge per labeled tx
    out_map: dict[str, list[str]] = {}
    in_map: dict[str, list[str]] = {}
    for _, row in edges_df.iterrows():
        u, v = str(row["txId1"]), str(row["txId2"])
        if u == v:
            continue
        out_map.setdefault(u, []).append(v)
        in_map.setdefault(v, []).append(u)

    rows: list[dict] = []
    labels_out: list[dict] = []

    for tid in node_ids:
        tid = str(tid)
        raw = class_map.get(tid, "unknown")
        if raw == "unknown":
            continue
        if raw == "1":
            y = 1
        elif raw == "2":
            y = 0
        else:
            continue

        if tid in out_map and out_map[tid]:
            succ = sorted(out_map[tid])[0]
            sender_wallet, receiver_wallet = tid, succ
        elif tid in in_map and in_map[tid]:
            pred = sorted(in_map[tid])[0]
            sender_wallet, receiver_wallet = pred, tid
        else:
            continue

        amt = float(amount_by_tx.get(tid, 0.0))
        rows.append(
            {
                "transaction_id": f"elliptic_{tid}",
                "sender_wallet": sender_wallet,
                "receiver_wallet": receiver_wallet,
                "amount": max(amt, 1e-8),
                "timestamp": _ts_for(tid),
                "label": y,
                "_primary_tx_id": tid,
            }
        )
        labels_out.append({"node_id": tid, "label": y, "split": "train"})

    if not rows:
        raise RuntimeError(
            "No labeled transactions with graph connectivity. "
            "Ensure elliptic_txs_classes.csv and edgelist are present and consistent."
        )

    tx_df = pd.DataFrame(rows)
    tx_df["timestamp"] = pd.to_datetime(tx_df["timestamp"], utc=True, errors="coerce")

    tx_feat = compute_transaction_features(tx_df)
    primary = tx_feat["_primary_tx_id"].astype(str)

    tx_feat["balance_ratio"] = primary.map(br_series).fillna(0.0)

    for col in ("unique_counterparties", "relay_pattern_score"):
        if col in graph_feat.columns:
            tx_feat[col] = primary.map(graph_feat[col]).fillna(0.0)
        else:
            tx_feat[col] = 0.0

    # Off-ramp / graph lens helpers (unprefixed names expected by trainers)
    for col in (
        "fan_in_ratio",
        "weighted_in",
        "in_degree",
        "suspicious_neighbor_ratio_1hop",
        "suspicious_neighbor_ratio_2hop",
    ):
        if col in graph_feat.columns:
            tx_feat[col] = primary.map(graph_feat[col]).fillna(0.0)
        else:
            tx_feat[col] = 0.0

    drop_cols = [c for c in ("_primary_tx_id", "_feat_row") if c in tx_feat.columns]
    tx_feat = tx_feat.drop(columns=drop_cols, errors="ignore")

    # Heuristic placeholders for lenses that expect these columns in reduced mode
    for h in ("heuristic_mean", "heuristic_max", "heuristic_triggered_count", "heuristic_top_confidence"):
        if h not in tx_feat.columns:
            tx_feat[h] = 0.0

    train_path = output_dir / "train_features.csv"
    tx_feat.to_csv(train_path, index=False)
    logger.info("Wrote %s (%d rows)", train_path.resolve(), len(tx_feat))

    edges_out = pd.DataFrame(edge_records)
    edges_out["timestamp"] = pd.to_datetime(edges_out["timestamp"], utc=True)
    edges_path = output_dir / "edges.csv"
    edges_out.to_csv(edges_path, index=False)
    logger.info("Wrote %s (%d edges)", edges_path.resolve(), len(edges_out))

    labels_path = output_dir / "node_labels.csv"
    pd.DataFrame(labels_out).to_csv(labels_path, index=False)
    logger.info("Wrote %s (%d labeled nodes)", labels_path.resolve(), len(labels_out))

    # Temporal trainer optional file
    wl_path = output_dir / "wallet_labels.csv"
    pd.DataFrame(
        [{"wallet": str(r["node_id"]), "label": int(r["label"])} for r in labels_out]
    ).to_csv(wl_path, index=False)
    logger.info("Wrote %s", wl_path.resolve())

    logger.info("Done. Example: python -m app.ml.training.train_behavioral --data-dir %s", output_dir)


if __name__ == "__main__":
    main()
