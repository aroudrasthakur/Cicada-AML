"""Graph-level (wallet node) features from a DiGraph and precomputed node metrics."""
from __future__ import annotations

from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)

_RISK_PR_THRESHOLD = 0.01


def compute_graph_features(
    G: nx.DiGraph,
    node_features: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Build a per-node feature table from ``G`` and ``compute_node_features`` output."""
    if G.number_of_nodes() == 0 or not node_features:
        logger.info("compute_graph_features: empty graph or node_features")
        return pd.DataFrame()

    rows = []
    for n in G.nodes():
        nf = node_features.get(n, {})
        ideg = int(nf.get("in_degree", 0) or 0)
        odeg = int(nf.get("out_degree", 0) or 0)
        wi = float(nf.get("weighted_in", 0.0) or 0.0)
        wo = float(nf.get("weighted_out", 0.0) or 0.0)
        denom = ideg + odeg + 1
        fan_in = ideg / denom
        fan_out = odeg / denom

        preds = set(G.predecessors(n))
        succs = set(G.successors(n))
        unique_cp = len(preds | succs)

        pr = float(nf.get("pagerank", 0.0) or 0.0)

        nbrs_1 = preds | succs
        if nbrs_1:
            risky_1 = sum(
                1
                for u in nbrs_1
                if float(node_features.get(u, {}).get("pagerank", 0.0) or 0.0) > _RISK_PR_THRESHOLD
            )
            sus_1 = risky_1 / len(nbrs_1)
        else:
            sus_1 = 0.0

        nbrs_2: set[Any] = set()
        for u in nbrs_1:
            nbrs_2.update(G.predecessors(u))
            nbrs_2.update(G.successors(u))
        nbrs_2.discard(n)
        if nbrs_2:
            risky_2 = sum(
                1
                for u in nbrs_2
                if float(node_features.get(u, {}).get("pagerank", 0.0) or 0.0) > _RISK_PR_THRESHOLD
            )
            sus_2 = risky_2 / len(nbrs_2)
        else:
            sus_2 = 0.0

        tv = float(nf.get("total_volume", wi + wo) or 0.0)
        relay_raw = (ideg * odeg) / (tv + 1.0)
        bal = float(nf.get("balance_ratio", 0.0) or 0.0)

        rows.append(
            {
                "node_id": n,
                "in_degree": ideg,
                "out_degree": odeg,
                "balance_ratio": bal,
                "weighted_in": wi,
                "weighted_out": wo,
                "fan_in_ratio": fan_in,
                "fan_out_ratio": fan_out,
                "unique_counterparties": unique_cp,
                "betweenness": float(nf.get("betweenness_centrality", 0.0) or 0.0),
                "pagerank": pr,
                "clustering_coeff": float(nf.get("clustering_coefficient", 0.0) or 0.0),
                "suspicious_neighbor_ratio_1hop": sus_1,
                "suspicious_neighbor_ratio_2hop": sus_2,
                "relay_pattern_score_raw": relay_raw,
            }
        )

    feat = pd.DataFrame(rows).set_index("node_id")
    mx = float(feat["relay_pattern_score_raw"].max()) if len(feat) else 0.0
    if mx > 0:
        feat["relay_pattern_score"] = feat["relay_pattern_score_raw"] / mx
    else:
        feat["relay_pattern_score"] = 0.0
    feat = feat.drop(columns=["relay_pattern_score_raw"], errors="ignore")
    return feat.replace([np.inf, -np.inf], 0.0).fillna(0.0)
