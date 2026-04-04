"""Cross-cutting red flag detection functions used by multiple heuristics."""
from __future__ import annotations

import numpy as np
from typing import Any, Optional


def check_sub_threshold_fragmentation(
    amounts: list[float], threshold: float = 10000.0
) -> tuple[bool, float]:
    """Check for transactions fragmented just below a threshold."""
    if not amounts:
        return False, 0.0
    below = [a for a in amounts if 0 < a < threshold]
    ratio = len(below) / len(amounts) if amounts else 0
    triggered = ratio > 0.7 and len(below) >= 3
    return triggered, ratio


def check_rapid_movement_low_balance(
    volumes: list[float], balances: list[float], threshold_ratio: float = 0.1
) -> tuple[bool, float]:
    """Check for high throughput with minimal retained balance."""
    if not volumes or not balances:
        return False, 0.0
    avg_vol = np.mean(volumes)
    avg_bal = np.mean(balances) if balances else 0
    if avg_vol == 0:
        return False, 0.0
    ratio = avg_bal / avg_vol
    return ratio < threshold_ratio, 1.0 - ratio


def check_circular_flows(
    graph: Any, node: str, max_length: int = 6
) -> tuple[bool, int]:
    """Check if node participates in cycles."""
    if graph is None:
        return False, 0
    try:
        from app.utils.graph_utils import detect_cycles
    except ImportError:
        return False, 0
    sub = graph.subgraph(
        list(graph.predecessors(node))
        + list(graph.successors(node))
        + [node]
    )
    cycles = detect_cycles(sub, max_length=max_length)
    node_cycles = [c for c in cycles if node in c]
    return len(node_cycles) > 0, len(node_cycles)


def check_many_to_one(
    graph: Any, node: str, threshold: int = 10
) -> tuple[bool, int]:
    """Check if many senders converge to one node."""
    if graph is None:
        return False, 0
    in_deg = graph.in_degree(node) if graph.has_node(node) else 0
    return in_deg >= threshold, in_deg


def check_one_to_many(
    graph: Any, node: str, threshold: int = 10
) -> tuple[bool, int]:
    """Check if one node fans out to many recipients."""
    if graph is None:
        return False, 0
    out_deg = graph.out_degree(node) if graph.has_node(node) else 0
    return out_deg >= threshold, out_deg


def check_high_risk_counterparty(
    wallet: Optional[dict], context: Optional[dict] = None
) -> tuple[bool, list[str]]:
    """Check exposure to known high-risk services/addresses."""
    if not context or "address_tags" not in context:
        return False, []
    tags = context.get("address_tags", {})
    risky_tags = {"mixer", "darknet", "ransomware", "sanctioned", "scam", "gambling"}
    found = [t for t in tags.values() if t.lower() in risky_tags]
    return len(found) > 0, found


def check_new_entity_high_value(
    wallet: Optional[dict],
    threshold_days: int = 7,
    threshold_amount: float = 10000.0,
) -> tuple[bool, dict]:
    """Check for new wallets handling high values immediately."""
    if not wallet:
        return False, {}
    from datetime import datetime, timezone

    first_seen = wallet.get("first_seen")
    total = wallet.get("total_in", 0) + wallet.get("total_out", 0)
    if not first_seen:
        return False, {}
    if isinstance(first_seen, str):
        try:
            from app.utils.time_utils import parse_timestamp
            first_seen = parse_timestamp(first_seen)
        except ImportError:
            from datetime import datetime as _dt
            first_seen = _dt.fromisoformat(first_seen)
    age = (datetime.now(timezone.utc) - first_seen).days
    triggered = age <= threshold_days and total >= threshold_amount
    return triggered, {"age_days": age, "total_volume": total}


def check_mule_patterns(
    wallet: Optional[dict], features: Optional[dict] = None
) -> tuple[bool, float]:
    """Check for mule-like behavior: quick pass-through with minimal retention."""
    if not wallet or not features:
        return False, 0.0
    total_in = wallet.get("total_in", 0)
    total_out = wallet.get("total_out", 0)
    if total_in == 0:
        return False, 0.0
    pass_through = total_out / total_in
    return pass_through > 0.9, pass_through


def check_no_economic_rationale(
    features: Optional[dict] = None,
) -> tuple[bool, float]:
    """Check for activity without clear economic purpose."""
    if not features:
        return False, 0.0
    relay = features.get("relay_pattern_score", 0)
    counterparties = features.get("unique_counterparties", 0)
    score = relay / (counterparties + 1)
    return score > 0.5, score


def check_tainted_to_cashout(
    features: Optional[dict] = None, context: Optional[dict] = None
) -> tuple[bool, float]:
    """Check for short path from tainted inflows to off-ramp."""
    if not features or not context:
        return False, 0.0
    inbound_risk = features.get("suspicious_neighbor_ratio_1hop", 0)
    is_near_exchange = context.get("near_exchange", False)
    score = inbound_risk * (2.0 if is_near_exchange else 1.0)
    return score > 0.5, min(score, 1.0)
