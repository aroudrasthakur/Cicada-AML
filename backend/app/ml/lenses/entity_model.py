"""Entity Lens: common control detection via community detection and clustering."""
import numpy as np
import joblib
from pathlib import Path
import networkx as nx

from app.ml.entity_pickle_compat import ensure_entity_epoch_logger_on_main
from app.ml.ml_device import xgb_predict_proba
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Must match train_entity._build_cluster_features (excluding cluster_id / label columns)
ENTITY_FEATURE_ORDER = [
    "size",
    "density",
    "internal_edges",
    "external_edges",
    "avg_in_degree",
    "avg_out_degree",
    "emb_mean_norm",
    "emb_std_mean",
]


class EntityLens:
    LENS_TAGS = ["entity"]

    def __init__(self):
        self.classifier = None
        self.feature_names: list[str] | None = None

    def detect_communities(self, G: nx.DiGraph) -> dict[str, int]:
        """Run Louvain community detection."""
        try:
            import community as community_louvain
        except ImportError:
            logger.warning("python-louvain not installed; all nodes assigned to community 0")
            return {n: 0 for n in G.nodes()}
        undirected = G.to_undirected()
        partition = community_louvain.best_partition(undirected)
        return partition

    def compute_cluster_features(
        self,
        G: nx.DiGraph,
        partition: dict,
        embeddings: np.ndarray | None = None,
        node_mapping: dict | None = None,
    ) -> dict:
        """Per-cluster features aligned with ``train_entity._build_cluster_features``."""
        from collections import defaultdict

        clusters: defaultdict[int, list] = defaultdict(list)
        for node, cid in partition.items():
            clusters[cid].append(node)

        # node_mapping from GraphLens: index -> wallet id
        node_to_idx: dict[str, int] = {}
        if node_mapping:
            for idx, w in node_mapping.items():
                node_to_idx[str(w)] = int(idx)

        cluster_features: dict[int, dict] = {}
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
            if embeddings is not None and node_mapping is not None:
                member_idx = [node_to_idx[str(m)] for m in members if str(m) in node_to_idx]
                if member_idx:
                    member_embs = embeddings[member_idx]
                    emb_mean = member_embs.mean(axis=0)
                    emb_std = member_embs.std(axis=0)

            cluster_features[cid] = {
                "cluster_id": cid,
                "size": n,
                "density": density,
                "internal_edges": internal_edges,
                "external_edges": external_edges,
                "avg_in_degree": total_in / max(n, 1),
                "avg_out_degree": total_out / max(n, 1),
                "emb_mean_norm": float(np.linalg.norm(emb_mean)),
                "emb_std_mean": float(np.mean(emb_std)),
                "members": members,
            }
        return cluster_features

    def predict(self, G: nx.DiGraph, heuristic_scores: dict = None, embeddings: np.ndarray = None, node_mapping: dict = None) -> dict:
        """Run entity resolution and cluster risk scoring.

        Uses the trained XGBoost classifier when loaded, otherwise falls back
        to a density-based heuristic.
        """
        partition = self.detect_communities(G)
        cluster_features = self.compute_cluster_features(G, partition, embeddings, node_mapping)

        cluster_scores: dict[int, float] = {}
        if self.classifier is not None:
            import pandas as pd

            cols = self.feature_names or ENTITY_FEATURE_ORDER
            rows = []
            cids = []
            for cid, cf in cluster_features.items():
                row = {c: cf.get(c, 0.0) for c in cols}
                rows.append(row)
                cids.append(cid)
            if rows:
                X = pd.DataFrame(rows)[cols].fillna(0).values.astype(np.float32)
                try:
                    probs = xgb_predict_proba(self.classifier, X)[:, 1]
                    for cid, prob in zip(cids, probs):
                        cluster_scores[cid] = float(prob)
                except Exception as exc:
                    logger.warning("Entity classifier inference failed, using fallback: %s", exc)

        entity_scores = {}
        for node in G.nodes():
            cid = partition.get(node, -1)
            if cid in cluster_scores:
                score = cluster_scores[cid]
            else:
                cf = cluster_features.get(cid, {})
                score = min(cf.get("density", 0) * cf.get("size", 1) / 100.0, 1.0)
            entity_scores[node] = {
                "entity_score": score,
                "cluster_id": cid,
                "cluster_risk_score": score,
            }
        return {"entity_scores": entity_scores, "partition": partition, "cluster_features": cluster_features}

    def load(self, model_path: str):
        p = Path(model_path)
        if p.exists():
            ensure_entity_epoch_logger_on_main()
            self.classifier = joblib.load(p)
            logger.info(f"Loaded entity classifier from {p}")
        names_p = p.parent / "feature_names.pkl"
        if names_p.exists():
            self.feature_names = joblib.load(names_p)
            logger.info("Loaded entity feature column order from %s", names_p)
