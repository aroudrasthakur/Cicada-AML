"""Generate human-readable explanations for transactions and cases."""
from app.repositories.scores_repo import get_transaction_score
from app.repositories.heuristics_repo import get_heuristic_result
from app.repositories.network_cases_repo import get_network_case
from app.ml.explainers import generate_explanation_text
from app.utils.logger import get_logger

logger = get_logger(__name__)


def explain_transaction(transaction_id: str) -> dict | None:
    """Generate explanation for a single transaction."""
    score = get_transaction_score(transaction_id)
    heuristic = get_heuristic_result(transaction_id)
    
    if not score:
        return None
    
    lens_scores = {
        "behavioral": score.get("behavioral_score", 0),
        "graph": score.get("graph_score", 0),
        "entity": score.get("entity_score", 0),
        "temporal": score.get("temporal_score", 0),
        "document": score.get("document_score", 0),
        "offramp": score.get("offramp_score", 0),
    }
    
    heuristic_data = heuristic or {}
    
    summary = generate_explanation_text(
        heuristic_results=heuristic_data,
        lens_scores=lens_scores,
        meta_score=score.get("meta_score", 0),
    )
    
    triggered = heuristic_data.get("triggered_ids", [])
    explanations = heuristic_data.get("explanations", {})
    
    return {
        "transaction_id": transaction_id,
        "heuristics_fired": [
            {"id": tid, "explanation": explanations.get(str(tid), "")}
            for tid in triggered
        ],
        "lens_contributions": lens_scores,
        "pattern_type": heuristic_data.get("top_typology"),
        "laundering_stage": _infer_stage(lens_scores),
        "summary": summary,
        "confidence": score.get("meta_score", 0),
        "coverage_tier": "tier0",
    }


def explain_case(case_id: str) -> dict | None:
    """Generate explanation for a network case."""
    case = get_network_case(case_id)
    if not case:
        return None
    
    return {
        "case_id": case_id,
        "heuristics_fired": [],
        "lens_contributions": {},
        "pattern_type": case.get("typology"),
        "laundering_stage": None,
        "summary": case.get("explanation", "No explanation available."),
        "confidence": case.get("risk_score", 0),
        "coverage_tier": "tier0",
    }


def _infer_stage(lens_scores: dict) -> str | None:
    """Infer likely laundering stage from lens score pattern."""
    offramp = lens_scores.get("offramp", 0) or 0
    graph = lens_scores.get("graph", 0) or 0
    behavioral = lens_scores.get("behavioral", 0) or 0
    
    if offramp > 0.5:
        return "integration"
    if graph > 0.5:
        return "layering"
    if behavioral > 0.5:
        return "placement"
    return None
