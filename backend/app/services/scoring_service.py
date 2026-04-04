"""Orchestrate ML inference and persist scores to Supabase."""
from app.ml.infer_pipeline import InferencePipeline
from app.repositories.scores_repo import upsert_transaction_scores, upsert_wallet_scores
from app.repositories.heuristics_repo import upsert_heuristic_results
from app.utils.logger import get_logger

logger = get_logger(__name__)

_pipeline: InferencePipeline | None = None


def get_pipeline() -> InferencePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = InferencePipeline()
        _pipeline.load_models()
    return _pipeline


def score_and_persist(transactions: list[dict]) -> list[dict]:
    """Run full scoring pipeline and persist results to database."""
    pipeline = get_pipeline()
    results = pipeline.score_transactions(transactions)
    
    heuristic_records = []
    score_records = []
    
    for r in results:
        tx_id = r.get("transaction_id")
        if not tx_id:
            continue
        
        heuristic_records.append({
            "transaction_id": tx_id,
            "heuristic_vector": r.get("heuristic_vector", []),
            "applicability_vector": r.get("applicability_vector", []),
            "triggered_ids": r.get("triggered_ids", []),
            "triggered_count": r.get("triggered_count", 0),
            "top_typology": r.get("top_typology"),
            "top_confidence": r.get("top_confidence"),
            "explanations": r.get("explanations", {}),
        })
        
        score_records.append({
            "transaction_id": tx_id,
            "behavioral_score": r.get("behavioral_score"),
            "behavioral_anomaly_score": r.get("behavioral_anomaly_score"),
            "graph_score": r.get("graph_score"),
            "entity_score": r.get("entity_score"),
            "temporal_score": r.get("temporal_score"),
            "document_score": r.get("document_score"),
            "offramp_score": r.get("offramp_score"),
            "meta_score": r.get("meta_score"),
            "predicted_label": r.get("predicted_label"),
            "explanation_summary": r.get("explanation_summary"),
        })
    
    if heuristic_records:
        upsert_heuristic_results(heuristic_records)
    if score_records:
        upsert_transaction_scores(score_records)
    
    logger.info(f"Scored and persisted {len(results)} transactions")
    return results
