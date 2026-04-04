"""Entity Lens: common control detection via community detection and clustering."""
import numpy as np
import joblib
from pathlib import Path
import networkx as nx
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EntityLens:
    LENS_TAGS = ["entity"]

    def __init__(self):
        self.classifier = None

    def detect_communities(self, G: nx.DiGraph) -> dict[str, int]:
        """Run Louvain community detection."""
        try:
            import community as community_louvain
            undirected = G.to_undirected()
            partition = community_louvain.best_partition(undirected)
            return partition
        except Exception as e:
            logger.warning(f"Community detection failed: {e}")
            return {n: 0 for n in G.nodes()}

    def compute_cluster_features(self, G: nx.DiGraph, partition: dict, embeddings: np.ndarray = None, node_mapping: dict = None) -> dict:
        """Compute per-cluster risk features."""
        from collections import defaultdict
        clusters = defaultdict(list)
        for node, cid in partition.items():
            clusters[cid].append(node)
        cluster_features = {}
        for cid, members in clusters.items():
            sub = G.subgraph(members)
            density = nx.density(sub) if len(members) > 1 else 0
            cluster_features[cid] = {
                "cluster_id": cid,
                "size": len(members),
                "density": density,
                "internal_edges": sub.number_of_edges(),
                "members": members,
            }
        return cluster_features

    def predict(self, G: nx.DiGraph, heuristic_scores: dict = None, embeddings: np.ndarray = None, node_mapping: dict = None) -> dict:
        """Run entity resolution and cluster risk scoring."""
        partition = self.detect_communities(G)
        cluster_features = self.compute_cluster_features(G, partition, embeddings, node_mapping)
        entity_scores = {}
        for node in G.nodes():
            cid = partition.get(node, -1)
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
            self.classifier = joblib.load(p)
            logger.info(f"Loaded entity classifier from {p}")
