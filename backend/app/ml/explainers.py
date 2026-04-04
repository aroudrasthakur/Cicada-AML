"""SHAP-based explanation and plain-English summary generation."""
from __future__ import annotations

from typing import Any

import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)


def explain_transaction(
    transaction_scores: dict[str, float],
    model: Any,
    feature_names: list[str],
    feature_values: np.ndarray | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Return top contributing features for an XGBoost prediction using SHAP.

    Falls back to model feature_importances_ when SHAP is unavailable.
    """
    try:
        import shap

        explainer = shap.TreeExplainer(model)
        if feature_values is not None:
            X = feature_values.reshape(1, -1) if feature_values.ndim == 1 else feature_values[:1]
            shap_values = explainer.shap_values(X)
            if isinstance(shap_values, list):
                sv = shap_values[1][0]
            else:
                sv = shap_values[0]
            contributions = []
            for i, (name, val) in enumerate(zip(feature_names, sv)):
                contributions.append({
                    "feature": name,
                    "shap_value": float(val),
                    "abs_shap": abs(float(val)),
                    "direction": "risk-increasing" if val > 0 else "risk-decreasing",
                    "feature_value": float(X[0, i]) if X.shape[1] > i else None,
                })
            contributions.sort(key=lambda x: x["abs_shap"], reverse=True)
            return contributions[:top_k]

        shap_values = explainer.shap_values(np.zeros((1, len(feature_names))))
        if isinstance(shap_values, list):
            sv = shap_values[1][0]
        else:
            sv = shap_values[0]
        contributions = [
            {"feature": name, "shap_value": float(val), "abs_shap": abs(float(val)),
             "direction": "risk-increasing" if val > 0 else "risk-decreasing", "feature_value": None}
            for name, val in zip(feature_names, sv)
        ]
        contributions.sort(key=lambda x: x["abs_shap"], reverse=True)
        return contributions[:top_k]

    except ImportError:
        logger.warning("SHAP not installed; falling back to feature_importances_")
    except Exception as exc:
        logger.warning("SHAP explanation failed: %s; falling back to feature_importances_", exc)

    return _fallback_importance(model, feature_names, top_k)


def _fallback_importance(model: Any, feature_names: list[str], top_k: int) -> list[dict[str, Any]]:
    """Use built-in feature importances when SHAP is unavailable."""
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return [{"feature": "unknown", "importance": 0.0, "direction": "unknown"}]

    pairs = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
    return [
        {"feature": name, "importance": float(imp), "direction": "risk-increasing"}
        for name, imp in pairs[:top_k]
    ]


def generate_explanation_text(
    heuristic_results: dict[str, Any],
    lens_scores: dict[str, float],
    meta_score: float,
    coverage_tier: str = "tier0",
) -> str:
    """Generate plain-English explanation from heuristic + lens + meta results.

    Also returns an audit trace via the ``_audit`` key when called through
    ``generate_explanation_with_audit``.
    """
    parts: list[str] = []
    audit_signals: dict[str, Any] = {}

    if meta_score >= 0.9:
        parts.append(f"This transaction is assessed as HIGH RISK (score: {meta_score:.2f}).")
    elif meta_score >= 0.5:
        parts.append(f"This transaction is assessed as MEDIUM RISK (score: {meta_score:.2f}).")
    else:
        parts.append(f"This transaction is assessed as LOW RISK (score: {meta_score:.2f}).")

    triggered = heuristic_results.get("triggered_count", 0)
    top_typology_raw = heuristic_results.get("top_typology")

    from app.ml.typology_taxonomy import heuristic_name_to_taxonomy
    top_typology_mapped = heuristic_name_to_taxonomy(top_typology_raw) if top_typology_raw else None
    display_typology = top_typology_mapped or top_typology_raw

    audit_signals["top_typology_raw"] = top_typology_raw
    audit_signals["top_typology_mapped"] = top_typology_mapped
    audit_signals["taxonomy_mapping_failed"] = (
        top_typology_raw is not None and top_typology_mapped is None
    )

    if triggered > 0:
        match_str = f' The strongest match is "{display_typology}"' if display_typology else ""
        conf = heuristic_results.get("top_confidence", 0)
        parts.append(
            f"{triggered} rule-based indicator(s) fired.{match_str}"
            f" (confidence: {conf:.2f})."
        )
    else:
        parts.append("No rule-based indicators were triggered.")

    active_lenses = {k: v for k, v in lens_scores.items() if v > 0.1 and not k.startswith("_")}
    if active_lenses:
        sorted_lenses = sorted(active_lenses.items(), key=lambda x: x[1], reverse=True)
        lens_strs = [f"{_humanize_lens(k)} ({v:.2f})" for k, v in sorted_lenses[:3]]
        parts.append(f"Key contributing signals: {', '.join(lens_strs)}.")
    else:
        parts.append("No ML lens produced a significant signal.")

    audit_signals["active_lenses"] = {k: round(v, 4) for k, v in active_lenses.items()}
    audit_signals["meta_score"] = round(meta_score, 4)

    anomaly = lens_scores.get("behavioral_anomaly_score", 0)
    if anomaly > 0.5:
        parts.append(
            f"The behavioral autoencoder detected unusual activity patterns "
            f"(anomaly score: {anomaly:.2f})."
        )

    if coverage_tier == "tier0":
        parts.append(
            "Note: This assessment is based on on-chain data only. "
            "Entity intelligence and off-chain KYC or supporting records were not available."
        )
    elif coverage_tier == "tier1":
        parts.append(
            "This assessment incorporates address tag intelligence. "
            "Full entity and richer off-chain context were not available."
        )

    text = " ".join(parts)

    if audit_signals.get("taxonomy_mapping_failed"):
        logger.warning(
            "explanation_audit | unmapped_typology=%s — raw class name leaked into text",
            top_typology_raw,
        )

    return text


def generate_explanation_with_audit(
    heuristic_results: dict[str, Any],
    lens_scores: dict[str, float],
    meta_score: float,
    coverage_tier: str = "tier0",
) -> dict[str, Any]:
    """Same as generate_explanation_text but returns ``{text, _audit}`` for traceability."""
    from app.ml.typology_taxonomy import heuristic_name_to_taxonomy

    top_raw = heuristic_results.get("top_typology")
    top_mapped = heuristic_name_to_taxonomy(top_raw) if top_raw else None
    active_lenses = {k: v for k, v in lens_scores.items() if v > 0.1 and not k.startswith("_")}

    text = generate_explanation_text(heuristic_results, lens_scores, meta_score, coverage_tier)
    return {
        "text": text,
        "_audit": {
            "top_typology_raw": top_raw,
            "top_typology_mapped": top_mapped,
            "taxonomy_mapping_failed": top_raw is not None and top_mapped is None,
            "active_lenses": {k: round(v, 4) for k, v in active_lenses.items()},
            "meta_score": round(meta_score, 4),
        },
    }


def _humanize_lens(key: str) -> str:
    """Convert internal lens key to human-readable label."""
    mapping = {
        "behavioral_score": "Behavioral Analysis",
        "behavioral_anomaly_score": "Behavioral Anomaly",
        "graph_score": "Graph Structure",
        "entity_score": "Entity Clustering",
        "temporal_score": "Temporal Patterns",
        "offramp_score": "Off-ramp Detection",
    }
    return mapping.get(key, key.replace("_", " ").title())
