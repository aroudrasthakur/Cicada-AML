"""Directed temporal graph construction and node-level metrics (NetworkX)."""
from __future__ import annotations

from typing import Any

import networkx as nx
import numpy as np

from app.utils.graph_utils import graph_to_cytoscape, k_hop_subgraph
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _wallet_pair(tx: dict[str, Any]) -> tuple[str | None, str | None]:
    sender = (
        tx.get("sender_wallet")
        or tx.get("sender")
        or tx.get("from")
        or tx.get("from_address")
    )
    receiver = (
        tx.get("receiver_wallet")
        or tx.get("receiver")
        or tx.get("to")
        or tx.get("to_address")
    )
    if sender is not None:
        sender = str(sender)
    if receiver is not None:
        receiver = str(receiver)
    return sender, receiver


def _tx_id(tx: dict[str, Any]) -> str | None:
    tid = tx.get("transaction_id") or tx.get("tx_hash") or tx.get("id")
    return str(tid) if tid is not None else None


def _edge_attrs(tx: dict[str, Any]) -> dict[str, Any]:
    amount = tx.get("amount")
    try:
        amount_f = float(amount) if amount is not None and not (isinstance(amount, float) and np.isnan(amount)) else 0.0
    except (TypeError, ValueError):
        amount_f = 0.0
    ts = tx.get("timestamp")
    asset = tx.get("token") if tx.get("token") is not None else tx.get("asset_type")
    tid = _tx_id(tx)
    return {
        "amount": amount_f,
        "timestamp": ts,
        "transaction_id": tid,
        "token": asset,
        "asset_type": asset,
    }


def build_wallet_graph(transactions: list[dict[str, Any]]) -> nx.DiGraph:
    """Wallet-address DiGraph: edges are transfers with amount, time, id, asset."""
    G = nx.DiGraph()
    if not transactions:
        logger.info("build_wallet_graph: empty transaction list")
        return G

    for tx in transactions:
        s, r = _wallet_pair(tx)
        if not s or not r or s == r:
            continue
        attrs = _edge_attrs(tx)
        if G.has_edge(s, r):
            prev = G[s][r]
            prev_amt = float(prev.get("amount", 0) or 0)
            attrs["amount"] = prev_amt + float(attrs.get("amount", 0) or 0)
            if attrs.get("timestamp") is None:
                attrs["timestamp"] = prev.get("timestamp")
            elif prev.get("timestamp") is not None:
                try:
                    if attrs["timestamp"] < prev["timestamp"]:
                        attrs["timestamp"] = prev["timestamp"]
                except TypeError:
                    pass
        G.add_edge(s, r, **attrs)

    logger.info("build_wallet_graph: nodes=%d edges=%d", G.number_of_nodes(), G.number_of_edges())
    return G


def build_transaction_graph(
    transactions: list[dict[str, Any]],
    edges_list: list[dict[str, Any]],
) -> nx.DiGraph:
    """Transaction-id DiGraph: nodes from transactions, edges from ``edges_list``."""
    G = nx.DiGraph()
    if not transactions and not edges_list:
        logger.info("build_transaction_graph: empty inputs")
        return G

    for tx in transactions:
        tid = _tx_id(tx)
        if not tid:
            continue
        G.add_node(tid, **{k: v for k, v in tx.items() if k not in ("transaction_id",)})

    for e in edges_list:
        u = e.get("source") or e.get("from") or e.get("source_transaction_id") or e.get("u")
        v = e.get("target") or e.get("to") or e.get("target_transaction_id") or e.get("v")
        if u is None or v is None:
            continue
        u, v = str(u), str(v)
        extra = {k: v for k, v in e.items() if k not in ("source", "target", "from", "to", "u", "v")}
        if G.has_edge(u, v):
            logger.debug("Duplicate transaction edge %s -> %s; overwriting attrs", u, v)
        G.add_edge(u, v, **extra)

    logger.info(
        "build_transaction_graph: nodes=%d edges=%d",
        G.number_of_nodes(),
        G.number_of_edges(),
    )
    return G


def compute_node_features(G: nx.DiGraph) -> dict[str, dict[str, Any]]:
    """Per-node degrees, volumes, balance ratio, centrality metrics."""
    if G.number_of_nodes() == 0:
        return {}

    nodes = list(G.nodes())
    result: dict[str, dict[str, Any]] = {n: {} for n in nodes}

    for n in nodes:
        w_in = 0.0
        w_out = 0.0
        for _, _, data in G.in_edges(n, data=True):
            w_in += float(data.get("amount", 0) or 0)
        for _, _, data in G.out_edges(n, data=True):
            w_out += float(data.get("amount", 0) or 0)
        ideg = int(G.in_degree(n))
        odeg = int(G.out_degree(n))
        vol = w_in + w_out
        denom = w_in + w_out
        if denom > 0:
            bal = (w_in - w_out) / denom
        else:
            bal = 0.0

        result[n].update(
            {
                "in_degree": ideg,
                "out_degree": odeg,
                "weighted_in": w_in,
                "weighted_out": w_out,
                "total_volume": vol,
                "balance_ratio": bal,
            }
        )

    try:
        between = nx.betweenness_centrality(G)
    except Exception as ex:
        logger.warning("betweenness_centrality failed: %s", ex)
        between = dict.fromkeys(nodes, 0.0)

    try:
        pr = nx.pagerank(G, alpha=0.85)
    except Exception as ex:
        logger.warning("pagerank failed: %s", ex)
        pr = dict.fromkeys(nodes, 0.0)

    try:
        und = G.to_undirected()
        clust = nx.clustering(und)
    except Exception as ex:
        logger.warning("clustering failed: %s", ex)
        clust = dict.fromkeys(nodes, 0.0)

    for n in nodes:
        result[n]["betweenness_centrality"] = float(between.get(n, 0.0) or 0.0)
        result[n]["pagerank"] = float(pr.get(n, 0.0) or 0.0)
        result[n]["clustering_coefficient"] = float(clust.get(n, 0.0) or 0.0)

    return result


def get_subgraph_for_wallet(G: nx.DiGraph, wallet: str, hops: int = 3) -> nx.DiGraph:
    """k-hop neighborhood around ``wallet`` (see ``app.utils.graph_utils``)."""
    if G.number_of_nodes() == 0 or wallet not in G:
        logger.info("get_subgraph_for_wallet: empty graph or missing wallet %s", wallet)
        return nx.DiGraph()
    k = max(0, int(hops))
    return k_hop_subgraph(G, wallet, k)


def get_wallet_graph_json(G: nx.DiGraph, wallet: str, hops: int = 3) -> dict:
    """Cytoscape.js elements JSON for the wallet k-hop subgraph."""
    sub = get_subgraph_for_wallet(G, wallet, hops=hops)
    return graph_to_cytoscape(sub)
