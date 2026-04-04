"""Train Graph Lens: 2-layer GAT on wallet transaction graph."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import average_precision_score, classification_report
from torch_geometric.data import Data

from app.ml.lenses.graph_model import GATClassifier
from app.ml.ml_device import log_device_banner, resolve_torch_device
from app.services.graph_service import build_wallet_graph, compute_node_features
from app.utils.logger import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("models/graph")
EPOCHS = 200
LR = 5e-3
PATIENCE = 30


def _load_data(data_dir: Path) -> tuple[pd.DataFrame, nx.DiGraph]:
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
    return labels_df, G


def _build_pyg_data(
    G: nx.DiGraph,
    node_features: dict,
    labels_df: pd.DataFrame | None,
) -> tuple[Data, dict[str, int]]:
    nodes = sorted(G.nodes())
    node_map = {n: i for i, n in enumerate(nodes)}

    feat_list = []
    for n in nodes:
        nf = node_features.get(n, {})
        feat_list.append([
            float(nf.get("in_degree", 0)),
            float(nf.get("out_degree", 0)),
            float(nf.get("weighted_in", 0)),
            float(nf.get("weighted_out", 0)),
            float(nf.get("betweenness_centrality", 0)),
            float(nf.get("pagerank", 0)),
            float(nf.get("clustering_coefficient", 0)),
        ])
    x = torch.FloatTensor(feat_list)

    edges = [(node_map[u], node_map[v]) for u, v in G.edges() if u in node_map and v in node_map]
    edge_index = torch.LongTensor(edges).t().contiguous() if edges else torch.zeros((2, 0), dtype=torch.long)

    y = torch.zeros(len(nodes), dtype=torch.long)
    train_mask = torch.zeros(len(nodes), dtype=torch.bool)
    val_mask = torch.zeros(len(nodes), dtype=torch.bool)

    if labels_df is not None and "node_id" in labels_df.columns and "label" in labels_df.columns:
        label_map = dict(zip(labels_df["node_id"].astype(str), labels_df["label"].astype(int)))
        split_map = dict(zip(labels_df["node_id"].astype(str), labels_df.get("split", pd.Series("train"))))
        for n, idx in node_map.items():
            if str(n) in label_map:
                y[idx] = label_map[str(n)]
                split = split_map.get(str(n), "train")
                if split == "val":
                    val_mask[idx] = True
                else:
                    train_mask[idx] = True

    if not train_mask.any():
        n_labeled = len(nodes)
        perm = torch.randperm(n_labeled)
        split = int(0.8 * n_labeled)
        train_mask[perm[:split]] = True
        val_mask[perm[split:]] = True

    data = Data(x=x, edge_index=edge_index, y=y, train_mask=train_mask, val_mask=val_mask)
    return data, node_map


def _train_gat(data: Data, device: torch.device) -> GATClassifier:
    data = data.to(device)
    in_channels = data.x.shape[1]
    model = GATClassifier(in_channels=in_channels, hidden_channels=64, heads=8, num_classes=2).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=5e-4)

    n_pos = int(data.y[data.train_mask].sum())
    n_neg = int(data.train_mask.sum()) - n_pos
    weight = torch.FloatTensor([1.0, max(n_neg / max(n_pos, 1), 1.0)]).to(device)
    logger.info("GAT class weights: %s", weight.tolist())

    best_ap, best_state, wait = 0.0, None, 0
    model.train()
    for epoch in range(1, EPOCHS + 1):
        optimizer.zero_grad()
        logits = model(data.x, data.edge_index)
        loss = F.cross_entropy(logits[data.train_mask], data.y[data.train_mask], weight=weight)
        loss.backward()
        optimizer.step()

        if epoch % 10 == 0 or epoch == 1:
            model.eval()
            with torch.no_grad():
                val_logits = model(data.x, data.edge_index)
                val_probs = F.softmax(val_logits, dim=1)[:, 1]
                if data.val_mask.any():
                    val_ap = average_precision_score(
                        data.y[data.val_mask].detach().cpu().numpy(),
                        val_probs[data.val_mask].detach().cpu().numpy(),
                    )
                else:
                    val_ap = 0.0
            logger.info("Epoch %d/%d  loss=%.4f  val_PR-AUC=%.4f", epoch, EPOCHS, loss.item(), val_ap)
            if val_ap > best_ap:
                best_ap = val_ap
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                wait = 0
            else:
                wait += 10
                if wait >= PATIENCE:
                    logger.info("Early stopping at epoch %d", epoch)
                    break
            model.train()

    if best_state is not None:
        model.load_state_dict(best_state)
    logger.info("Best validation PR-AUC: %.4f", best_ap)

    model.eval()
    with torch.no_grad():
        val_logits = model(data.x, data.edge_index)
        val_probs = F.softmax(val_logits, dim=1)[:, 1]
        if data.val_mask.any():
            y_val = data.y[data.val_mask].detach().cpu().numpy()
            p_val = val_probs[data.val_mask].detach().cpu().numpy()
            logger.info("\n%s", classification_report(y_val, (p_val >= 0.5).astype(int), zero_division=0))
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Graph Lens GAT model")
    parser.add_argument("--data-dir", default="data/processed", help="Directory with preprocessed data")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    logger.info("=== Training Graph Lens ===")
    log_device_banner(logger, "train_graph")
    device = resolve_torch_device()
    labels_df, G = _load_data(data_dir)
    logger.info("Graph: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())

    node_features = compute_node_features(G)
    data, node_map = _build_pyg_data(G, node_features, labels_df)
    logger.info("PyG data: %d nodes, %d edges, %d features", data.x.shape[0], data.edge_index.shape[1], data.x.shape[1])

    model = _train_gat(data, device)

    model.eval()
    with torch.no_grad():
        embeddings = model.get_embeddings(data.x, data.edge_index).detach().cpu().numpy()
    inv_map = {v: k for k, v in node_map.items()}
    logger.info("Extracted node embeddings: shape %s", embeddings.shape)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"model_state_dict": model.state_dict(), "in_channels": data.x.shape[1]},
        OUTPUT_DIR / "gat_model.pt",
    )
    np.save(OUTPUT_DIR / "node_embeddings.npy", embeddings)
    with open(OUTPUT_DIR / "node_mapping.json", "w") as f:
        json.dump({str(v): str(k) for k, v in node_map.items()}, f)
    logger.info("Artifacts saved to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
