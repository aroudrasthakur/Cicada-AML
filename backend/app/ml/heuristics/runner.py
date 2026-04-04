"""Execute all registered heuristics for a transaction/wallet."""
from __future__ import annotations
from typing import Any, Optional
from app.ml.heuristics.base import HeuristicResult, Applicability
from app.ml.heuristics import registry
from app.utils.logger import get_logger

logger = get_logger(__name__)

TOTAL_HEURISTICS = 185
# Treat any non-trivial confidence as a fired heuristic (some implementations set
# confidence but omit ``triggered=True``).
_CONFIDENCE_FIRED_EPS = 1e-9


def run_all(
    tx: Optional[dict] = None,
    wallet: Optional[dict] = None,
    graph: Any = None,
    features: Optional[dict] = None,
    context: Optional[dict] = None,
) -> dict:
    """Run all registered heuristics and return aggregated results.
    
    Returns dict with keys:
        heuristic_vector: list[float] (185 confidence scores, 0.0 for non-triggered)
        applicability_vector: list[str] (185 applicability statuses)
        triggered_ids: list[int] (IDs that fired)
        triggered_count: int
        top_typology: str | None
        top_confidence: float | None
        explanations: dict[str, str] (triggered_id -> explanation)
    """
    all_heuristics = registry.get_all()
    
    heuristic_vector = [0.0] * TOTAL_HEURISTICS
    applicability_vector = ["applicable"] * TOTAL_HEURISTICS
    triggered_ids = []
    explanations = {}
    
    for hid in range(1, TOTAL_HEURISTICS + 1):
        h = all_heuristics.get(hid)
        if h is None:
            # Not yet implemented — mark as inapplicable
            applicability_vector[hid - 1] = "inapplicable_missing_data"
            continue
        
        try:
            # Check data requirements first
            applicability = h.check_data_requirements(context)
            if applicability != Applicability.APPLICABLE:
                applicability_vector[hid - 1] = applicability.value
                continue
            
            result: HeuristicResult = h.evaluate(
                tx=tx, wallet=wallet, graph=graph, features=features, context=context,
            )
            
            applicability_vector[hid - 1] = result.applicability.value
            
            if result.applicability != Applicability.APPLICABLE:
                continue
            
            conf = float(result.confidence) if result.confidence is not None else 0.0
            heuristic_vector[hid - 1] = conf

            fired = bool(result.triggered) or conf > _CONFIDENCE_FIRED_EPS
            if fired:
                triggered_ids.append(hid)
                if result.explanation:
                    explanations[str(hid)] = result.explanation
                
        except Exception as exc:
            logger.error(f"Heuristic {hid} ({getattr(h, 'name', '?')}) failed: {exc}")
            applicability_vector[hid - 1] = "inapplicable_missing_data"
    
    top_typology = None
    top_confidence = None
    top_k_triggers: list[dict] = []
    if triggered_ids:
        ranked = sorted(triggered_ids, key=lambda i: heuristic_vector[i - 1], reverse=True)
        for hid in ranked[:5]:
            h = all_heuristics.get(hid)
            top_k_triggers.append({
                "heuristic_id": hid,
                "name": getattr(h, "name", f"heuristic_{hid}"),
                "confidence": heuristic_vector[hid - 1],
            })
        best = top_k_triggers[0]
        top_typology = best["name"]
        top_confidence = best["confidence"]

    inapplicable_count = sum(1 for a in applicability_vector if a != "applicable")
    logger.info(
        "heuristic_trace | triggered=%d/%d inapplicable=%d top_k=%s",
        len(triggered_ids), TOTAL_HEURISTICS, inapplicable_count,
        [(t["name"], round(t["confidence"], 3)) for t in top_k_triggers],
    )

    return {
        "heuristic_vector": heuristic_vector,
        "applicability_vector": applicability_vector,
        "triggered_ids": triggered_ids,
        "triggered_count": len(triggered_ids),
        "top_typology": top_typology,
        "top_confidence": top_confidence,
        "top_k_triggers": top_k_triggers,
        "explanations": explanations,
    }
