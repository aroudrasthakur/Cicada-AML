"""Execute all registered heuristics for a transaction/wallet."""
from __future__ import annotations
from typing import Any, Optional
from app.ml.heuristics.base import HeuristicResult, Applicability
from app.ml.heuristics import registry
from app.utils.logger import get_logger

logger = get_logger(__name__)

TOTAL_HEURISTICS = 185


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
            
            heuristic_vector[hid - 1] = result.confidence
            
            if result.triggered:
                triggered_ids.append(hid)
                explanations[str(hid)] = result.explanation
                
        except Exception as exc:
            logger.error(f"Heuristic {hid} ({getattr(h, 'name', '?')}) failed: {exc}")
            applicability_vector[hid - 1] = "inapplicable_missing_data"
    
    top_typology = None
    top_confidence = None
    if triggered_ids:
        best_idx = max(triggered_ids, key=lambda i: heuristic_vector[i - 1])
        best_h = all_heuristics.get(best_idx)
        top_typology = best_h.name if best_h else f"heuristic_{best_idx}"
        top_confidence = heuristic_vector[best_idx - 1]
    
    return {
        "heuristic_vector": heuristic_vector,
        "applicability_vector": applicability_vector,
        "triggered_ids": triggered_ids,
        "triggered_count": len(triggered_ids),
        "top_typology": top_typology,
        "top_confidence": top_confidence,
        "explanations": explanations,
    }
