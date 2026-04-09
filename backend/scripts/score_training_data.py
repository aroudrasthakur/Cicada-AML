"""Score ``train_features.csv`` with every trained lens and write lens-enriched columns.

Produces ``train_features_scored.csv`` (or overwrites ``train_features.csv`` with
``--inplace``) that ``prepare_meta_features`` can then consume so the meta-learner
trains on **real** stacked lens signals instead of zeros.

Usage (from ``backend/``)::

    python -m scripts.score_training_data --data-dir ../data/processed

The script loads each trained lens model from ``models/`` and runs inference:

* **Behavioral** – XGBoost + Autoencoder on tabular features.
* **Graph** – GAT softmax probs looked up via saved node embeddings + mapping.
* **Entity** – XGBoost on cluster features via saved partition + classifier.
* **Temporal** – LSTM on per-wallet sequences (vectorized build).
* **Off-ramp** – XGBoost on off-ramp tabular features.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch

from app.ml.entity_pickle_compat import ensure_entity_epoch_logger_on_main
from app.ml.model_paths import MODELS_DIR
from app.ml.ml_device import resolve_torch_device, xgb_predict_proba
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Behavioral
# ---------------------------------------------------------------------------
def _score_behavioral(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return (behavioral_score, behavioral_anomaly_score) arrays aligned to df rows."""
    xgb_path = MODELS_DIR / "behavioral" / "xgboost_behavioral.pkl"
    ae_path = MODELS_DIR / "behavioral" / "autoencoder_behavioral.pt"
    scaler_path = MODELS_DIR / "behavioral" / "scaler_behavioral.pkl"

    cols = [c for c in [
        "amount", "log_amount", "fee_ratio", "is_round_amount",
        "burstiness_score", "amount_deviation", "sender_tx_count",
        "receiver_tx_count", "sender_repeat_count",
        "balance_ratio", "unique_counterparties", "relay_pattern_score",
    ] if c in df.columns]
    X = df[cols].fillna(0).values.astype(np.float32) if cols else np.zeros((len(df), 1), dtype=np.float32)

    scaler = joblib.load(scaler_path) if scaler_path.exists() else None
    if scaler is not None:
        X = scaler.transform(X)

    beh_score = np.zeros(len(df), dtype=np.float64)
    anomaly_score = np.zeros(len(df), dtype=np.float64)

    if xgb_path.exists():
        xgb_model = joblib.load(xgb_path)
        beh_score = xgb_predict_proba(xgb_model, X)[:, 1].astype(np.float64)
        logger.info("Behavioral XGBoost scored %d rows", len(df))

    if ae_path.exists():
        from app.ml.lenses.behavioral_model import BehavioralAutoencoder
        device = resolve_torch_device()
        state = torch.load(ae_path, map_location=device, weights_only=True)
        input_dim = state.get("input_dim", X.shape[1])
        ae = BehavioralAutoencoder(input_dim)
        ae.load_state_dict(state["model_state_dict"])
        anomaly_threshold = state.get("anomaly_threshold", 1.0)
        if anomaly_threshold <= 0: anomaly_threshold = 1.0
        ae.to(device).eval()
        with torch.no_grad():
            t = torch.FloatTensor(X).to(device)
            recon = ae(t)
            mse = ((t - recon) ** 2).mean(dim=1).cpu().numpy().astype(np.float64)
            anomaly_score = np.clip(mse / anomaly_threshold, 0.0, 1.0)
        logger.info("Behavioral autoencoder scored %d rows", len(df))

    return beh_score, anomaly_score


# ---------------------------------------------------------------------------
# Graph (fast lookup via saved embeddings + node_mapping)
# ---------------------------------------------------------------------------
def _score_graph(df: pd.DataFrame) -> np.ndarray:
    """Per-transaction graph_score via the trained GAT + saved embeddings."""
    model_path = MODELS_DIR / "graph" / "gat_model.pt"
    mapping_path = MODELS_DIR / "graph" / "node_mapping.json"
    emb_path = MODELS_DIR / "graph" / "node_embeddings.npy"

    if not model_path.exists() or not mapping_path.exists() or not emb_path.exists():
        logger.warning("Graph artifacts incomplete; returning zeros")
        return np.zeros(len(df), dtype=np.float64)

    device = resolve_torch_device()
    state = torch.load(model_path, map_location=device, weights_only=True)
    from app.ml.lenses.graph_model import build_graph_model
    in_ch = state.get("in_channels", 7)
    model = build_graph_model(
        state.get("model_type", "gat"),
        in_ch,
        hidden_channels=state.get("hidden_channels", 64),
        heads=state.get("heads", 8),
        num_classes=2,
        dropout=state.get("dropout", 0.3),
    )
    model.load_state_dict(state["model_state_dict"])
    model.to(device).eval()

    with open(mapping_path) as f:
        idx_to_node = json.load(f)
    node_to_idx = {str(v): int(k) for k, v in idx_to_node.items()}

    edges_path = Path(MODELS_DIR).parent / "data" / "processed" / "edges.csv"
    if not edges_path.exists():
        edges_path = Path(MODELS_DIR).parents[0].parent / "data" / "processed" / "edges.csv"

    logger.info("Building graph edge_index for scoring...")
    edges_df = pd.read_csv(edges_path) if edges_path.exists() else pd.DataFrame()

    n_nodes = len(idx_to_node)
    src_col = "source" if "source" in edges_df.columns else "sender_wallet"
    dst_col = "target" if "target" in edges_df.columns else "receiver_wallet"

    if not edges_df.empty and src_col in edges_df.columns and dst_col in edges_df.columns:
        valid_edges = edges_df.dropna(subset=[src_col, dst_col])
        src_strs = valid_edges[src_col].astype(str)
        dst_strs = valid_edges[dst_col].astype(str)
        edge_src = src_strs.map(node_to_idx).dropna()
        edge_dst = dst_strs.map(node_to_idx).dropna()
        
        # Keep only edges where both ends are in mapping
        valid_mask = edge_src.index.intersection(edge_dst.index)
        edge_src_arr = edge_src.loc[valid_mask].astype(int).values
        edge_dst_arr = edge_dst.loc[valid_mask].astype(int).values

        if len(edge_src_arr) > 0:
            edge_index = torch.tensor([edge_src_arr, edge_dst_arr], dtype=torch.long).to(device)
        else:
            edge_index = torch.zeros((2, 0), dtype=torch.long, device=device)
            
        from app.services.graph_service import build_wallet_graph, compute_node_features
        # Build G to compute correct node features (C-5 fix)
        edge_records = []
        for s, d, amt in zip(src_strs, dst_strs, valid_edges.get("amount", pd.Series(0, index=valid_edges.index))):
            edge_records.append({"sender_wallet": s, "receiver_wallet": d, "amount": float(amt)})
        G = build_wallet_graph(edge_records)
        node_feats = compute_node_features(G, global_metrics="full")
        
        node_features_np = np.zeros((n_nodes, in_ch), dtype=np.float32)
        for w, idx in node_to_idx.items():
            if w in node_feats:
                nf = node_feats[w]
                node_features_np[idx] = [
                    float(nf.get("in_degree", 0)),
                    float(nf.get("out_degree", 0)),
                    float(nf.get("weighted_in", 0.0)),
                    float(nf.get("weighted_out", 0.0)),
                    float(nf.get("betweenness_centrality", 0.0)),
                    float(nf.get("pagerank", 0.0)),
                    float(nf.get("clustering_coefficient", 0.0)),
                ][:in_ch]
    else:
        edge_index = torch.zeros((2, 0), dtype=torch.long, device=device)
        node_features_np = np.zeros((n_nodes, in_ch), dtype=np.float32)

    from torch_geometric.data import Data as PygData
    x_t = torch.FloatTensor(node_features_np).to(device)
    data = PygData(x=x_t, edge_index=edge_index)

    with torch.no_grad():
        logits = model(data.x, data.edge_index)
        probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()

    send_col = "sender_wallet" if "sender_wallet" in df.columns else "sender"
    scores = np.zeros(len(df), dtype=np.float64)
    for i, wallet in enumerate(df[send_col].astype(str).values):
        idx = node_to_idx.get(wallet)
        if idx is not None:
            scores[i] = float(probs[idx])
    logger.info("Graph lens scored %d rows (%.1f%% matched)", len(df), 100 * (scores > 0).mean())
    return scores


# ---------------------------------------------------------------------------
# Entity (cluster-level XGBoost via saved partition)
# ---------------------------------------------------------------------------
def _score_entity(df: pd.DataFrame) -> np.ndarray:
    cls_path = MODELS_DIR / "entity" / "entity_classifier.pkl"
    part_path = MODELS_DIR / "entity" / "partition.json"
    feat_path = MODELS_DIR / "entity" / "feature_names.pkl"
    emb_path = MODELS_DIR / "graph" / "node_embeddings.npy"
    mapping_path = MODELS_DIR / "graph" / "node_mapping.json"

    if not cls_path.exists() or not part_path.exists():
        logger.warning("Entity artifacts incomplete; returning zeros")
        return np.zeros(len(df), dtype=np.float64)

    ensure_entity_epoch_logger_on_main()
    classifier = joblib.load(cls_path)
    feature_names = joblib.load(feat_path) if feat_path.exists() else None

    with open(part_path) as f:
        partition = json.load(f)

    node_to_idx = {}
    embeddings = None
    if mapping_path.exists() and emb_path.exists():
        with open(mapping_path) as f:
            idx_to_node = json.load(f)
        node_to_idx = {str(v): int(k) for k, v in idx_to_node.items()}
        embeddings = np.load(emb_path)

    clusters: dict[int, list[str]] = defaultdict(list)
    for node, cid in partition.items():
        clusters[int(cid)].append(str(node))

    edges_path = Path(MODELS_DIR).parent / "data" / "processed" / "edges.csv"
    edges_df = pd.read_csv(edges_path) if edges_path.exists() else pd.DataFrame()

    adj: dict[str, set[str]] = defaultdict(set)
    for _, row in edges_df.iterrows():
        s = str(row.get("source", row.get("sender_wallet", "")))
        d = str(row.get("target", row.get("receiver_wallet", "")))
        adj[s].add(d)
        adj[d].add(s)

    cluster_scores: dict[int, float] = {}
    rows_for_cls = []
    cids_ordered = []

    for cid, members in clusters.items():
        size = len(members)
        member_set = set(members)
        internal = sum(1 for m in members for nb in adj.get(m, set()) if nb in member_set)
        external = sum(1 for m in members for nb in adj.get(m, set()) if nb not in member_set)
        density = internal / max(size * (size - 1), 1)
        avg_in = np.mean([len([nb for nb in adj.get(m, set()) if nb in member_set]) for m in members]) if members else 0
        avg_out = np.mean([len([nb for nb in adj.get(m, set()) if nb not in member_set]) for m in members]) if members else 0

        emb_mean_norm = 0.0
        emb_std_mean = 0.0
        if embeddings is not None:
            idxs = [node_to_idx[m] for m in members if m in node_to_idx]
            if idxs:
                embs = embeddings[idxs]
                emb_mean_norm = float(np.linalg.norm(embs.mean(axis=0)))
                emb_std_mean = float(embs.std(axis=0).mean())

        row = {
            "size": size,
            "density": density,
            "internal_edges": internal,
            "external_edges": external,
            "avg_in_degree": avg_in,
            "avg_out_degree": avg_out,
            "emb_mean_norm": emb_mean_norm,
            "emb_std_mean": emb_std_mean,
        }
        rows_for_cls.append(row)
        cids_ordered.append(cid)

    if rows_for_cls:
        X_cls = pd.DataFrame(rows_for_cls)
        if feature_names:
            for c in feature_names:
                if c not in X_cls.columns:
                    X_cls[c] = 0.0
            X_cls = X_cls[feature_names]
        X_arr = X_cls.fillna(0).values.astype(np.float32)
        try:
            probs = xgb_predict_proba(classifier, X_arr)[:, 1]
            for cid, prob in zip(cids_ordered, probs):
                cluster_scores[cid] = float(prob)
        except Exception as e:
            logger.warning("Entity classifier failed: %s", e)

    send_col = "sender_wallet" if "sender_wallet" in df.columns else "sender"
    scores = np.zeros(len(df), dtype=np.float64)
    for i, wallet in enumerate(df[send_col].astype(str).values):
        cid_str = partition.get(wallet)
        if cid_str is not None:
            scores[i] = cluster_scores.get(int(cid_str), 0.0)
    logger.info("Entity lens scored %d rows (%.1f%% matched)", len(df), 100 * (scores > 0).mean())
    return scores


# ---------------------------------------------------------------------------
# Temporal (vectorized sequence build then batch LSTM)
# ---------------------------------------------------------------------------
def _score_temporal(df: pd.DataFrame) -> np.ndarray:
    model_path = MODELS_DIR / "temporal" / "lstm_model.pt"
    if not model_path.exists():
        logger.warning("Temporal model not found; returning zeros")
        return np.zeros(len(df), dtype=np.float64)

    device = resolve_torch_device()
    state = torch.load(model_path, map_location=device, weights_only=True)
    input_dim = state.get("input_dim", 4)

    from app.ml.lenses.temporal_model import TemporalLSTM, MAX_SEQ_LEN
    model = TemporalLSTM(input_dim)
    model.load_state_dict(state["model_state_dict"])
    model.to(device).eval()

    send_col = "sender_wallet" if "sender_wallet" in df.columns else "sender"
    recv_col = "receiver_wallet" if "receiver_wallet" in df.columns else "receiver"

    work = df.copy()
    if "timestamp" in work.columns:
        work["timestamp"] = pd.to_datetime(work["timestamp"], utc=True, errors="coerce")
        work = work.sort_values("timestamp")

    logger.info("Building wallet sequences for temporal scoring...")
    wallet_txns: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(work.itertuples(index=False)):
        s = str(getattr(row, send_col, ""))
        r = str(getattr(row, recv_col, ""))
        if s:
            wallet_txns[s].append(i)
        if r and r != s:
            wallet_txns[r].append(i)

    amount = work["amount"].fillna(0).values.astype(np.float32)
    tspo = work["time_since_prev_out"].fillna(0).values.astype(np.float32) if "time_since_prev_out" in work.columns else np.zeros(len(work), np.float32)
    burst = work["burstiness_score"].fillna(0).values.astype(np.float32) if "burstiness_score" in work.columns else np.zeros(len(work), np.float32)
    senders = work[send_col].astype(str).values

    unique_wallets = list(wallet_txns.keys())
    sequences = np.zeros((len(unique_wallets), MAX_SEQ_LEN, input_dim), dtype=np.float32)

    for wi, wallet in enumerate(unique_wallets):
        idxs = wallet_txns[wallet][-MAX_SEQ_LEN:]
        for si, ti in enumerate(idxs):
            offset = MAX_SEQ_LEN - len(idxs) + si
            sequences[wi, offset, 0] = amount[ti]
            sequences[wi, offset, 1] = tspo[ti]
            sequences[wi, offset, 2] = 1.0 if senders[ti] == wallet else 0.0
            sequences[wi, offset, 3] = burst[ti]

    wallet_score: dict[str, float] = {}
    BATCH = 512
    for start in range(0, len(unique_wallets), BATCH):
        batch = sequences[start:start + BATCH]
        with torch.no_grad():
            t = torch.FloatTensor(batch).to(device)
            logits = model(t).cpu().numpy()
            probs = 1.0 / (1.0 + np.exp(-logits))
        for j, prob in enumerate(probs):
            wallet_score[unique_wallets[start + j]] = float(prob)

    tx_scores = np.zeros(len(df), dtype=np.float64)
    orig_senders = df[send_col].astype(str).values
    for i, w in enumerate(orig_senders):
        tx_scores[i] = wallet_score.get(w, 0.0)

    logger.info("Temporal lens scored %d rows (%d wallets)", len(df), len(unique_wallets))
    return tx_scores


# ---------------------------------------------------------------------------
# Off-ramp
# ---------------------------------------------------------------------------
def _score_offramp(df: pd.DataFrame) -> np.ndarray:
    cls_path = MODELS_DIR / "offramp" / "offramp_classifier.pkl"
    if not cls_path.exists():
        logger.warning("Off-ramp model not found; returning zeros")
        return np.zeros(len(df), dtype=np.float64)

    cols = [c for c in [
        "fan_in_ratio", "weighted_in", "in_degree",
        "suspicious_neighbor_ratio_1hop", "suspicious_neighbor_ratio_2hop",
        "amount", "log_amount", "relay_pattern_score",
        "heuristic_mean", "heuristic_max", "heuristic_triggered_count",
        "heuristic_top_confidence",
    ] if c in df.columns]
    X = df[cols].fillna(0).values.astype(np.float32) if cols else np.zeros((len(df), 1), dtype=np.float32)
    classifier = joblib.load(cls_path)
    scores = xgb_predict_proba(classifier, X)[:, 1].astype(np.float64)
    logger.info("Off-ramp lens scored %d rows", len(df))
    return scores


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score train_features.csv with all trained lens models",
    )
    parser.add_argument(
        "--data-dir", type=Path, default=Path("../data/processed"),
        help="Directory with train_features.csv",
    )
    parser.add_argument(
        "--inplace", action="store_true",
        help="Overwrite train_features.csv instead of writing train_features_scored.csv",
    )
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    train_path = data_dir / "train_features.csv"
    if not train_path.exists():
        logger.error("Not found: %s", train_path)
        sys.exit(1)

    df = pd.read_csv(train_path)
    logger.info("Loaded %d rows from %s", len(df), train_path)

    beh, beh_anom = _score_behavioral(df)
    df["behavioral_score"] = beh
    df["behavioral_anomaly_score"] = beh_anom

    df["graph_score"] = _score_graph(df)
    df["entity_score"] = _score_entity(df)
    df["temporal_score"] = _score_temporal(df)
    df["offramp_score"] = _score_offramp(df)

    df["heuristic_triggered_ratio"] = (
        df["heuristic_triggered_count"] / 185.0
        if "heuristic_triggered_count" in df.columns
        else 0.0
    )
    for c in ["has_entity_intel", "has_address_tags",
              "coverage_tier_0", "coverage_tier_1", "coverage_tier_2",
              "n_lenses_available"]:
        if c not in df.columns:
            df[c] = 0.0
    df["n_lenses_available"] = (
        (df["behavioral_score"] > 0).astype(int)
        + (df["graph_score"] > 0).astype(int)
        + (df["entity_score"] > 0).astype(int)
        + (df["temporal_score"] > 0).astype(int)
        + (df["offramp_score"] > 0).astype(int)
    )

    out_path = train_path if args.inplace else (data_dir / "train_features_scored.csv")
    df.to_csv(out_path, index=False)
    logger.info("Wrote %s (%d rows, %d columns)", out_path, len(df), len(df.columns))

    for col in ["behavioral_score", "behavioral_anomaly_score", "graph_score",
                "entity_score", "temporal_score", "offramp_score"]:
        vals = df[col].values
        logger.info(
            "  %-30s  min=%.4f  mean=%.4f  max=%.4f  nonzero=%.1f%%",
            col, vals.min(), vals.mean(), vals.max(), 100 * (vals != 0).mean(),
        )


if __name__ == "__main__":
    main()
