"""Community detection and cluster analysis."""
import numpy as np
import networkx as nx
from collections import defaultdict
from app.utils.logger import get_logger

logger = get_logger(__name__)


def detect_communities_louvain(G: nx.DiGraph) -> dict[str, int]:
    """Run Louvain community detection on the graph."""
    try:
        import community as community_louvain
        undirected = G.to_undirected()
        partition = community_louvain.best_partition(undirected)
        logger.info(f"Louvain detected {len(set(partition.values()))} communities")
        return partition
    except ImportError:
        logger.warning("python-louvain not installed, falling back to connected components")
        return _fallback_components(G)


def detect_communities_leiden(G: nx.DiGraph) -> dict[str, int]:
    """Run Leiden community detection."""
    try:
        import igraph as ig
        import leidenalg
        
        nodes = list(G.nodes())
        node_map = {n: i for i, n in enumerate(nodes)}
        edges = [(node_map[u], node_map[v]) for u, v in G.edges() if u in node_map and v in node_map]
        
        ig_graph = ig.Graph(n=len(nodes), edges=edges, directed=True)
        partition = leidenalg.find_partition(ig_graph, leidenalg.ModularityVertexPartition)
        
        result = {}
        for cid, members in enumerate(partition):
            for idx in members:
                result[nodes[idx]] = cid
        
        logger.info(f"Leiden detected {len(partition)} communities")
        return result
    except ImportError:
        logger.warning("leidenalg not installed, falling back to Louvain")
        return detect_communities_louvain(G)


def _fallback_components(G: nx.DiGraph) -> dict[str, int]:
    """Fallback: use connected components as communities."""
    undirected = G.to_undirected()
    partition = {}
    for cid, component in enumerate(nx.connected_components(undirected)):
        for node in component:
            partition[node] = cid
    return partition


def compute_cluster_risk(G: nx.DiGraph, partition: dict, node_risk_scores: dict[str, float] = None) -> dict[int, dict]:
    """Compute risk metrics for each community cluster."""
    clusters = defaultdict(list)
    for node, cid in partition.items():
        clusters[cid].append(node)
    
    result = {}
    for cid, members in clusters.items():
        sub = G.subgraph(members)
        density = nx.density(sub) if len(members) > 1 else 0
        
        risk_scores = []
        if node_risk_scores:
            risk_scores = [node_risk_scores.get(m, 0) for m in members]
        
        result[cid] = {
            "cluster_id": cid,
            "size": len(members),
            "density": density,
            "internal_edges": sub.number_of_edges(),
            "mean_risk": float(np.mean(risk_scores)) if risk_scores else 0.0,
            "max_risk": float(np.max(risk_scores)) if risk_scores else 0.0,
            "members": members,
        }
    
    return result
