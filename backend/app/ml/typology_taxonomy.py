"""AML typology labels for clusters: aml_non_peel_chain patterns + peel/layering.

The legacy classifier used max fan-in/out > 10 and avg degree < 2.5, so small graphs
almost always became "peel chain" or "layering". This module:

- Reads optional ground-truth columns on uploaded CSVs (typology / aml_pattern / …).
- Maps heuristic ``top_typology`` names (e.g. FanOutDispersal) to user-facing labels.
- Uses **adaptive** structural thresholds based on subgraph size.
- Detects cross-chain activity from ``chain_id`` / ``chain`` diversity.
- Uses off-ramp lens scores when present.
"""
from __future__ import annotations

import re
from collections import Counter
from statistics import median
from typing import Any

import networkx as nx

from app.utils.graph_utils import detect_cycles

# Canonical user-facing strings (match product language)
MANY_TO_ONE = "many-to-one collection"
CROSS_CHAIN = "cross-chain bridge hop"
FAN_OUT = "fan-out"
CIRCULAR = "circular loop / round-tripping"
RECONSOLIDATION = "reconsolidation"
OFFRAMP = "offramp exits"
PEEL = "peel chain"
LAYERING = "layering"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def normalize_ground_truth_label(raw: str) -> str | None:
    """Map dataset / analyst string to one of the canonical typology labels."""
    if not raw or not str(raw).strip():
        return None
    s = _norm(str(raw))
    # Direct contains / aliases (aml_non_peel_chain and common variants)
    if "many" in s and "to" in s and "one" in s:
        return MANY_TO_ONE
    if "many-to-one" in s or "many to one" in s or ("fan" in s and "in" in s and "aggregat" in s):
        return MANY_TO_ONE
    if "bridge" in s or ("cross" in s and "chain" in s) or "hop" in s and "bridge" in s:
        return CROSS_CHAIN
    if "fan" in s and "out" in s or "dispersal" in s:
        return FAN_OUT
    if "circular" in s or "round" in s and "trip" in s or "roundtrip" in s or "loop" in s:
        return CIRCULAR
    if "reconsolid" in s or "re-consolid" in s:
        return RECONSOLIDATION
    if "offramp" in s or "off-ramp" in s or ("off" in s and "exit" in s and "ramp" in s):
        return OFFRAMP
    if "peel" in s:
        return PEEL
    if "layer" in s:
        return LAYERING
    return None


def extract_ground_truth_label(tx: dict[str, Any]) -> str | None:
    """Scan transaction row for typology / pattern columns (case-insensitive keys)."""
    for k, v in tx.items():
        if v is None:
            continue
        ks = str(k).lower().replace(" ", "_")
        if not any(
            x in ks
            for x in (
                "typology",
                "aml_pattern",
                "ml_pattern",
                "pattern_type",
                "laundering_typology",
                "money_laundering",
            )
        ):
            continue
        try:
            if isinstance(v, float) and str(v) == "nan":
                continue
        except Exception:
            pass
        raw = str(v).strip()
        if not raw:
            continue
        mapped = normalize_ground_truth_label(raw)
        if mapped:
            return mapped
    return None


def ground_truth_mode(transactions: list[dict[str, Any]]) -> str | None:
    labels = []
    for tx in transactions:
        c = extract_ground_truth_label(tx)
        if c:
            labels.append(c)
    if not labels:
        return None
    return Counter(labels).most_common(1)[0][0]


def cross_chain_from_transactions(transactions: list[dict[str, Any]]) -> bool:
    chains: set[str] = set()
    for tx in transactions:
        for key in ("chain_id", "chain", "blockchain", "network"):
            v = tx.get(key)
            if v is None or (isinstance(v, float) and str(v) == "nan"):
                continue
            s = str(v).strip().lower()
            if s and s not in ("", "none", "null"):
                chains.add(s)
    return len(chains) >= 2


def heuristic_name_to_taxonomy(heuristic_name: str | None) -> str | None:
    """Map registered heuristic class name to user-facing typology."""
    if not heuristic_name:
        return None
    n = heuristic_name.replace(" ", "")

    # Explicit IDs (blockchain.py and related)
    exact = {
        "PeelChain": PEEL,
        "FanOutDispersal": FAN_OUT,
        "FanInAggregation": MANY_TO_ONE,
        "ConsolidationAfterObfuscation": RECONSOLIDATION,
        "CrossWalletChainLoops": CROSS_CHAIN,
        "AutonomousCrossChainExecution": CROSS_CHAIN,
        "SelfTransferChain": CIRCULAR,
        "OTCBrokerLayering": OFFRAMP,
        "NestedVASPExposure": OFFRAMP,
        "TimeDelayLayering": LAYERING,
        "LayeredHopsFreshWallets": LAYERING,
    }
    if n in exact:
        return exact[n]

    low = n.lower()
    if "peelchain" in low or low == "peel_chain":
        return PEEL
    if "fanout" in low or "fan_out" in low or "dispersal" in low:
        return FAN_OUT
    if "fanin" in low or "fan_in" in low or "aggregation" in low:
        return MANY_TO_ONE
    if "cross" in low and "chain" in low or "bridge" in low:
        return CROSS_CHAIN
    if "consolidat" in low and "obfuscat" in low:
        return RECONSOLIDATION
    if "selftransfer" in low or "round" in low and "trip" in low:
        return CIRCULAR
    if "otc" in low or "offramp" in low or "nestedvasp" in low:
        return OFFRAMP
    if "layer" in low and "time" in low:
        return LAYERING
    return None


def weighted_heuristic_vote(scoring_rows: list[dict[str, Any]]) -> str | None:
    """Aggregate ``heuristic_top_typology`` across transactions in the cluster."""
    weights: Counter[str] = Counter()
    for r in scoring_rows:
        name = r.get("heuristic_top_typology")
        if not name:
            continue
        mapped = heuristic_name_to_taxonomy(str(name))
        if not mapped:
            continue
        conf = float(r.get("heuristic_top_confidence") or 0)
        weights[mapped] += max(0.05, conf)
    if not weights:
        return None
    return weights.most_common(1)[0][0]


def offramp_strong(scoring_rows: list[dict[str, Any]], threshold: float = 0.42) -> bool:
    vals = [float(r.get("offramp_score") or 0) for r in scoring_rows if r.get("offramp_score") is not None]
    if not vals:
        return False
    return float(median(vals)) >= threshold


def _reconsolidation_hint(G: nx.DiGraph) -> bool:
    """Merge-after-split: a sink with ≥2 predecessors, at least two of which branch further."""
    for n in G.nodes():
        if G.in_degree(n) < 2:
            continue
        preds = list(G.predecessors(n))
        branching = sum(1 for p in preds if G.out_degree(p) >= 2)
        if branching >= 2:
            return True
    return False


def structure_typology(G: nx.DiGraph) -> str:
    """Graph-only typology with **size-adaptive** fan thresholds (fixes small-graph peel bias)."""
    n_nodes = G.number_of_nodes()
    if n_nodes == 0:
        return LAYERING

    max_out = max((G.out_degree(nd) for nd in G.nodes()), default=0)
    max_in = max((G.in_degree(nd) for nd in G.nodes()), default=0)
    cycles = detect_cycles(G, max_length=8)

    # Scale fan thresholds down for subgraphs (was hardcoded 10 → never fired)
    fan_thr = max(3, min(10, 2 + n_nodes // 3))

    if max_out >= fan_thr:
        return FAN_OUT
    if max_in >= fan_thr:
        return MANY_TO_ONE

    if _reconsolidation_hint(G):
        return RECONSOLIDATION

    if len(cycles) > 0:
        return CIRCULAR

    avg_deg = sum(G.degree(nd) for nd in G.nodes()) / max(n_nodes, 1)
    if avg_deg < 2.5:
        return PEEL
    return LAYERING


def infer_cluster_typology(
    G: nx.DiGraph,
    *,
    transactions: list[dict[str, Any]],
    scoring_rows: list[dict[str, Any]] | None = None,
) -> str:
    """Dominant typology for a wallet cluster used in pipeline runs and investigations."""
    scoring_rows = scoring_rows or []

    gt = ground_truth_mode(transactions)
    if gt:
        return gt

    if cross_chain_from_transactions(transactions):
        return CROSS_CHAIN

    hv = weighted_heuristic_vote(scoring_rows)
    st = structure_typology(G)

    # Resolve peel vs structural patterns (runner often picks PeelChain on sparse graphs)
    if hv == PEEL and st in (FAN_OUT, MANY_TO_ONE, CIRCULAR, RECONSOLIDATION):
        base = st
    elif hv and hv != LAYERING:
        base = hv
    else:
        base = st

    if offramp_strong(scoring_rows) and base in (LAYERING, PEEL):
        return OFFRAMP

    return base
