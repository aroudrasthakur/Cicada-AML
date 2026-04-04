"""Orchestrates transaction, graph, and subgraph feature pipelines."""
from __future__ import annotations

from typing import Any, Literal

import networkx as nx
import pandas as pd

from app.ml.graph_features import compute_graph_features
from app.ml.subgraph_features import compute_subgraph_features
from app.ml.transaction_features import compute_transaction_features
from app.services.graph_service import compute_node_features
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _transactions_to_dataframe(transactions: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(transactions or [])
    if df.empty:
        return df
    out = df.copy()
    if "sender_wallet" not in out.columns:
        for alt in ("sender", "from", "from_address"):
            if alt in out.columns:
                out["sender_wallet"] = out[alt].astype(str)
                break
    if "receiver_wallet" not in out.columns:
        for alt in ("receiver", "to", "to_address"):
            if alt in out.columns:
                out["receiver_wallet"] = out[alt].astype(str)
                break
    return out


def compute_all_features(
    transactions: list[dict[str, Any]],
    graph: nx.DiGraph,
    *,
    global_metrics: Literal["full", "none"] = "full",
) -> dict[str, Any]:
    """Run all feature extractors and return separate tables plus a merged view."""
    df = _transactions_to_dataframe(transactions)
    transaction_features = compute_transaction_features(df)

    if graph.number_of_nodes() == 0:
        logger.info("compute_all_features: empty graph; graph/subgraph features empty")
        empty = pd.DataFrame()
        combined = transaction_features.copy() if not transaction_features.empty else empty
        return {
            "transaction_features": transaction_features,
            "graph_features": empty,
            "subgraph_features": empty,
            "combined": combined,
            "node_features": {},
        }

    node_feats = compute_node_features(graph, global_metrics=global_metrics)
    graph_features = compute_graph_features(graph, node_feats)
    subgraph_features = compute_subgraph_features(graph, df)

    combined = transaction_features.copy() if not transaction_features.empty else pd.DataFrame()
    if combined.empty:
        logger.info("compute_all_features: no transactions; combined graph-only stub")
        if not graph_features.empty:
            combined = graph_features.copy()
            combined["transaction_id"] = None
    else:
        if "sender_wallet" not in combined.columns or "receiver_wallet" not in combined.columns:
            logger.warning("combined merge skipped: missing sender_wallet/receiver_wallet")
        else:
            if not graph_features.empty:
                combined = combined.merge(
                    graph_features.add_prefix("sender_graph_"),
                    left_on="sender_wallet",
                    right_index=True,
                    how="left",
                )
                combined = combined.merge(
                    graph_features.add_prefix("receiver_graph_"),
                    left_on="receiver_wallet",
                    right_index=True,
                    how="left",
                )
            if not subgraph_features.empty:
                combined = combined.merge(
                    subgraph_features.add_prefix("sender_sub_"),
                    left_on="sender_wallet",
                    right_index=True,
                    how="left",
                )
                combined = combined.merge(
                    subgraph_features.add_prefix("receiver_sub_"),
                    left_on="receiver_wallet",
                    right_index=True,
                    how="left",
                )
            num_cols = combined.select_dtypes(include=["float64", "float32", "int64", "int32"]).columns
            combined[num_cols] = combined[num_cols].fillna(0)

            # Training stores sender graph metrics without prefix; lenses select these names.
            for col in (
                "balance_ratio",
                "unique_counterparties",
                "relay_pattern_score",
                "fan_in_ratio",
                "weighted_in",
                "in_degree",
                "suspicious_neighbor_ratio_1hop",
                "suspicious_neighbor_ratio_2hop",
            ):
                src = f"sender_graph_{col}"
                if src in combined.columns:
                    combined[col] = combined[src]
                elif col not in combined.columns:
                    combined[col] = 0.0

    return {
        "transaction_features": transaction_features,
        "graph_features": graph_features,
        "subgraph_features": subgraph_features,
        "combined": combined,
        "node_features": node_feats,
    }
