"""Train Entity Lens: Louvain clustering + XGBoost on cluster-level features."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import joblib
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from app.services.graph_service import build_wallet_graph
from app.utils.logger import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("models/entity")
EMBEDDINGS_PATH = Path("models/graph/node_embeddings.npy")
NODE_MAP_PATH = Path("models/graph/node_mapping.json")


def _load_data(data_dir: Path) -> tuple[nx.DiGraph, pd.DataFrame | None]:
    edges_path = data_dir / "edges.csv"
    labels_path = data_dir / "node_labels.csv"
    if not edges_path.exists():
        logger.error("Edge list not found at %s", edges_path)
        logger.info(
            "Run the feature pipeline first:\n"
            "  python -m scripts.prepare_features --output %s",
            data_dir,
        )
        sys.exit(1)
    edges_df = pd.read_csv(edges_path)
    G = build_wallet_graph(edges_df.to_dict("records"))
    labels_df = pd.read_csv(labels_path) if labels_path.exists() else None
    return G, labels_df


def _load_embeddings() -> tuple[np.ndarray | None, dict | None]:
    if not EMBEDDINGS_PATH.exists():
        logger.warning("Node embeddings not found at %s — training without embeddings", EMBEDDINGS_PATH)
        return None, None
    embeddings = np.load(EMBEDDINGS_PATH)
    node_map = None
    if NODE_MAP_PATH.exists():
        with open(NODE_MAP_PATH) as f:
            node_map = json.load(f)
    logger.info("Loaded node embeddings: shape %s", embeddings.shape)
    return embeddings, node_map


def _run_louvain(G: nx.DiGraph) -> dict[str, int]:
    try:
        import community as community_louvain
        undirected = G.to_undirected()
        partition = community_louvain.best_partition(undirected, random_state=42)
        logger.info("Louvain found %d communities", len(set(partition.values())))
        return partition
    except ImportError:
        logger.warning("python-louvain not installed; falling back to connected components")
        partition = {}
        for cid, comp in enumerate(nx.weakly_connected_components(G)):
            for n in comp:
                partition[n] = cid
        return partition


def _build_cluster_features(
    G: nx.DiGraph,
    partition: dict[str, int],
    embeddings: np.ndarray | None,
    node_map: dict | None,
) -> pd.DataFrame:
    clusters: defaultdict[int, list] = defaultdict(list)
    for node, cid in partition.items():
        clusters[cid].append(node)

    rows = []
    for cid, members in clusters.items():
        sub = G.subgraph(members)
        n = len(members)
        density = nx.density(sub) if n > 1 else 0.0
        internal_edges = sub.number_of_edges()
        total_in = sum(dict(G.in_degree(members)).values())
        total_out = sum(dict(G.out_degree(members)).values())
        external_edges = total_in + total_out - 2 * internal_edges

        emb_mean = np.zeros(1)
        emb_std = np.zeros(1)
        if embeddings is not None and node_map is not None:
            idx_map = {v: int(k) for k, v in node_map.items()}
            member_idx = [idx_map[str(m)] for m in members if str(m) in idx_map]
            if member_idx:
                member_embs = embeddings[member_idx]
                emb_mean = member_embs.mean(axis=0)
                emb_std = member_embs.std(axis=0)

        row = {
            "cluster_id": cid,
            "size": n,
            "density": density,
            "internal_edges": internal_edges,
            "external_edges": external_edges,
            "avg_in_degree": total_in / max(n, 1),
            "avg_out_degree": total_out / max(n, 1),
            "emb_mean_norm": float(np.linalg.norm(emb_mean)),
            "emb_std_mean": float(emb_std.mean()),
        }
        rows.append(row)

    return pd.DataFrame(rows)


def _assign_cluster_labels(
    cluster_df: pd.DataFrame,
    partition: dict[str, int],
    labels_df: pd.DataFrame | None,
) -> pd.DataFrame:
    if labels_df is None or "node_id" not in labels_df.columns:
        logger.warning("No node labels — generating synthetic cluster labels from density heuristic")
        cluster_df["label"] = (cluster_df["density"] > cluster_df["density"].quantile(0.9)).astype(int)
        return cluster_df

    node_labels = dict(zip(labels_df["node_id"].astype(str), labels_df["label"].astype(int)))
    cluster_illicit_frac = {}
    clusters: defaultdict[int, list] = defaultdict(list)
    for node, cid in partition.items():
        clusters[cid].append(node)
    for cid, members in clusters.items():
        labels = [node_labels.get(str(m), 0) for m in members]
        cluster_illicit_frac[cid] = np.mean(labels) if labels else 0.0

    cluster_df["illicit_fraction"] = cluster_df["cluster_id"].map(cluster_illicit_frac).fillna(0)
    cluster_df["label"] = (cluster_df["illicit_fraction"] >= 0.5).astype(int)
    return cluster_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Entity Lens classifier")
    parser.add_argument("--data-dir", default="data/processed", help="Directory with preprocessed data")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    logger.info("=== Training Entity Lens ===")
    G, labels_df = _load_data(data_dir)
    embeddings, node_map = _load_embeddings()
    partition = _run_louvain(G)
    cluster_df = _build_cluster_features(G, partition, embeddings, node_map)
    cluster_df = _assign_cluster_labels(cluster_df, partition, labels_df)

    feature_cols = [c for c in cluster_df.columns if c not in ("cluster_id", "label", "illicit_fraction")]
    X = cluster_df[feature_cols].fillna(0).values.astype(np.float32)
    y = cluster_df["label"].values.astype(int)

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    spw = n_neg / max(n_pos, 1)
    logger.info("Cluster balance: %d pos / %d neg → scale_pos_weight=%.2f", n_pos, n_neg, spw)

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        scale_pos_weight=spw,
        eval_metric="aucpr",
        early_stopping_rounds=15,
        random_state=42,
        use_label_encoder=False,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    y_prob = model.predict_proba(X_val)[:, 1]
    pr_auc = average_precision_score(y_val, y_prob)
    logger.info("Entity XGBoost PR-AUC on validation: %.4f", pr_auc)
    logger.info("\n%s", classification_report(y_val, (y_prob >= 0.5).astype(int), zero_division=0))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUTPUT_DIR / "entity_classifier.pkl")
    joblib.dump(feature_cols, OUTPUT_DIR / "feature_names.pkl")
    with open(OUTPUT_DIR / "partition.json", "w") as f:
        json.dump({str(k): int(v) for k, v in partition.items()}, f)
    logger.info("Artifacts saved to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
