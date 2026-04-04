"""End-to-end inference pipeline: heuristics-first, then ML lenses, then meta-learner."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import joblib
import networkx as nx
import numpy as np
import pandas as pd

from app.config import settings
from app.ml.heuristics.runner import run_all as run_heuristics
from app.ml.lenses.behavioral_model import BehavioralLens
from app.ml.lenses.document_model import DocumentLens
from app.ml.lenses.entity_model import EntityLens
from app.ml.lenses.graph_model import GraphLens
from app.ml.lenses.offramp_model import OfframpLens
from app.ml.lenses.temporal_model import TemporalLens
from app.services.data_availability_service import assess_data_availability
from app.services.feature_service import compute_all_features
from app.services.graph_service import compute_node_features
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InferencePipeline:
    """Orchestrates the full Aegis-AML scoring pipeline.

    Ordering contract:
        1. Feature extraction
        2. Heuristics (always first — zero-ML fallback)
        3. Parallel lenses: behavioral, graph, temporal, document, offramp
        4. Entity lens (depends on graph embeddings from step 3)
        5. Meta-learner on stacked scores
        6. Threshold decision
    """

    def __init__(self) -> None:
        self.behavioral = BehavioralLens()
        self.graph = GraphLens()
        self.entity = EntityLens()
        self.temporal = TemporalLens()
        self.document = DocumentLens()
        self.offramp = OfframpLens()
        self.meta_model = None
        self.meta_feature_names: list[str] = []
        self.threshold_config: dict = {}
        self._loaded = False

    def load_models(self) -> None:
        """Load all trained model artifacts from config paths."""
        logger.info("Loading model artifacts...")
        self.behavioral.load(settings.behavioral_model_path, settings.behavioral_ae_path)
        self.graph.load(settings.graph_model_path)
        self.entity.load(settings.entity_model_path)
        self.temporal.load(settings.temporal_model_path)
        self.document.load(settings.document_model_path)
        self.offramp.load(settings.offramp_model_path)

        meta_path = Path(settings.meta_model_path)
        if meta_path.exists():
            self.meta_model = joblib.load(meta_path)
            logger.info("Loaded meta-learner from %s", meta_path)
        meta_names_path = meta_path.parent / "feature_names.pkl"
        if meta_names_path.exists():
            self.meta_feature_names = joblib.load(meta_names_path)

        threshold_path = Path(settings.threshold_policy_path)
        if threshold_path.exists():
            with open(threshold_path) as f:
                self.threshold_config = json.load(f)
            logger.info("Loaded threshold config: %s", self.threshold_config)
        else:
            self.threshold_config = {
                "decision_threshold": settings.fallback_risk_threshold,
                "high_risk_threshold": 0.9,
                "low_risk_ceiling": 0.3,
            }

        self._loaded = True
        logger.info("All models loaded")

    def score_transactions(
        self,
        transactions: list[dict[str, Any]],
        graph: nx.DiGraph | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Full pipeline: features → heuristics → lenses → meta → threshold → results."""
        if not self._loaded:
            self.load_models()

        context = context or {}
        
        # Build graph if not provided
        if graph is None:
            from app.services.graph_service import build_wallet_graph
            graph = build_wallet_graph(transactions)
            logger.info("Built graph from transactions: %d nodes, %d edges", 
                       graph.number_of_nodes(), graph.number_of_edges())

        # --- 1. Feature extraction ---
        all_features = compute_all_features(transactions, graph)
        tx_features = all_features["transaction_features"]
        combined = all_features["combined"]
        node_features = compute_node_features(graph) if graph.number_of_nodes() > 0 else {}

        data_flags = assess_data_availability(
            has_transactions=len(transactions) > 0,
            has_address_tags=context.get("has_address_tags", False),
            has_entity_links=context.get("has_entity_links", False),
            has_document_events=context.get("has_document_events", False),
        )

        results = []
        for i, tx in enumerate(transactions):
            row_features = combined.iloc[[i]] if i < len(combined) else pd.DataFrame()

            # --- 2. Heuristics (always first) ---
            h_result = run_heuristics(
                tx=tx,
                wallet=tx.get("sender_wallet") or tx.get("sender"),
                graph=graph,
                features=row_features.to_dict("records")[0] if not row_features.empty else {},
                context=context,
            )
            h_vec = np.array(h_result["heuristic_vector"], dtype=np.float32)

            # --- 3. Parallel lens group: behavioral, graph, temporal, document, offramp ---
            lens_scores = self._run_parallel_lenses(
                tx, row_features, graph, node_features, h_vec, data_flags, context,
            )

            # --- 4. Entity lens (depends on graph embeddings) ---
            entity_out = self.entity.predict(
                graph,
                heuristic_scores={},
                embeddings=lens_scores.get("_graph_embeddings"),
                node_mapping=lens_scores.get("_graph_node_mapping"),
            )
            wallet_id = str(tx.get("sender_wallet") or tx.get("sender", ""))
            entity_info = entity_out["entity_scores"].get(wallet_id, {})
            lens_scores["entity_score"] = entity_info.get("entity_score", 0.0)

            # --- 5. Meta-learner ---
            meta_score = self._run_meta(lens_scores, h_result, data_flags)

            # --- 6. Threshold decision ---
            decision_threshold = self.threshold_config.get("decision_threshold", 0.5)
            high_threshold = self.threshold_config.get("high_risk_threshold", 0.9)
            low_ceiling = self.threshold_config.get("low_risk_ceiling", 0.3)

            if meta_score >= high_threshold:
                risk_level = "high"
            elif meta_score >= decision_threshold:
                risk_level = "medium"
            elif meta_score <= low_ceiling:
                risk_level = "low"
            else:
                risk_level = "medium-low"

            results.append({
                "transaction_id": tx.get("transaction_id") or tx.get("id", f"tx_{i}"),
                "meta_score": float(meta_score),
                "risk_level": risk_level,
                "behavioral_score": float(lens_scores.get("behavioral_score", 0)),
                "behavioral_anomaly_score": float(lens_scores.get("behavioral_anomaly_score", 0)),
                "graph_score": float(lens_scores.get("graph_score", 0)),
                "entity_score": float(lens_scores.get("entity_score", 0)),
                "temporal_score": float(lens_scores.get("temporal_score", 0)),
                "document_score": float(lens_scores.get("document_score", 0)),
                "offramp_score": float(lens_scores.get("offramp_score", 0)),
                "heuristic_vector": h_result["heuristic_vector"],
                "applicability_vector": h_result["applicability_vector"],
                "triggered_ids": h_result["triggered_ids"],
                "heuristic_triggered_count": h_result["triggered_count"],
                "heuristic_top_typology": h_result["top_typology"],
                "heuristic_top_confidence": h_result["top_confidence"],
                "heuristic_explanations": h_result["explanations"],
                "coverage_tier": data_flags.coverage_tier.value,
                "decision_threshold": decision_threshold,
            })

        logger.info("Scored %d transactions", len(results))
        return results

    def _run_parallel_lenses(
        self,
        tx: dict,
        row_features: pd.DataFrame,
        graph: nx.DiGraph,
        node_features: dict,
        h_vec: np.ndarray,
        data_flags: Any,
        context: dict,
    ) -> dict[str, Any]:
        """Run independent lenses in parallel, aggregate scores."""
        scores: dict[str, Any] = {}

        def _behavioral() -> None:
            out = self.behavioral.predict(row_features, h_vec)
            scores["behavioral_score"] = float(np.mean(out["behavioral_score"]))
            scores["behavioral_anomaly_score"] = float(np.mean(out["behavioral_anomaly_score"]))

        def _graph() -> None:
            out = self.graph.predict(graph, node_features)
            wallet_id = str(tx.get("sender_wallet") or tx.get("sender", ""))
            inv = out.get("node_mapping", {})
            node_idx = {v: k for k, v in inv.items()}.get(wallet_id)
            scores["graph_score"] = float(out["graph_score"][node_idx]) if node_idx is not None else 0.0
            scores["_graph_embeddings"] = out.get("embeddings")
            scores["_graph_node_mapping"] = out.get("node_mapping")

        def _temporal() -> None:
            wallet_id = str(tx.get("sender_wallet") or tx.get("sender", ""))
            df = row_features if not row_features.empty else pd.DataFrame([tx])
            out = self.temporal.predict(df, [wallet_id])
            scores["temporal_score"] = out["temporal_scores"].get(wallet_id, 0.0)

        def _document() -> None:
            doc_events = context.get("document_events") if data_flags.has_document_intel else None
            out = self.document.predict(row_features if not row_features.empty else None, h_vec, doc_events)
            scores["document_score"] = float(np.mean(out["document_score"]))

        def _offramp() -> None:
            out = self.offramp.predict(row_features if not row_features.empty else pd.DataFrame(), h_vec)
            scores["offramp_score"] = float(np.mean(out["offramp_score"]))

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [
                pool.submit(_behavioral),
                pool.submit(_graph),
                pool.submit(_temporal),
                pool.submit(_document),
                pool.submit(_offramp),
            ]
            for fut in futures:
                try:
                    fut.result(timeout=30)
                except Exception as exc:
                    logger.error("Lens execution failed: %s", exc)

        return scores

    def _run_meta(
        self,
        lens_scores: dict[str, Any],
        h_result: dict,
        data_flags: Any,
    ) -> float:
        """Assemble meta feature vector and predict."""
        h_vec = np.array(h_result["heuristic_vector"], dtype=np.float32)
        triggered = h_result["triggered_count"]
        h_nonzero = h_vec[h_vec > 0]

        meta_dict = {
            "behavioral_score": lens_scores.get("behavioral_score", 0),
            "behavioral_anomaly_score": lens_scores.get("behavioral_anomaly_score", 0),
            "graph_score": lens_scores.get("graph_score", 0),
            "entity_score": lens_scores.get("entity_score", 0),
            "temporal_score": lens_scores.get("temporal_score", 0),
            "document_score": lens_scores.get("document_score", 0),
            "offramp_score": lens_scores.get("offramp_score", 0),
            "heuristic_mean": float(h_nonzero.mean()) if len(h_nonzero) > 0 else 0.0,
            "heuristic_max": float(h_vec.max()),
            "heuristic_triggered_count": triggered,
            "heuristic_top_confidence": float(h_result["top_confidence"] or 0),
            "heuristic_triggered_ratio": triggered / max(len(h_vec), 1),
            "has_entity_intel": float(data_flags.has_entity_intel),
            "has_document_intel": float(data_flags.has_document_intel),
            "has_address_tags": float(data_flags.has_address_tags),
            "coverage_tier_0": float(data_flags.coverage_tier.value == "tier0"),
            "coverage_tier_1": float(data_flags.coverage_tier.value == "tier1"),
            "coverage_tier_2": float(data_flags.coverage_tier.value == "tier2"),
            "n_lenses_available": sum(1 for k in (
                "behavioral_score", "graph_score", "entity_score",
                "temporal_score", "document_score", "offramp_score",
            ) if lens_scores.get(k, 0) != 0),
        }

        if self.meta_model is not None:
            feature_order = self.meta_feature_names or list(meta_dict.keys())
            X = np.array([[meta_dict.get(f, 0.0) for f in feature_order]], dtype=np.float32)
            return float(self.meta_model.predict_proba(X)[0, 1])

        # Fallback: weighted average when meta-model is not trained yet
        weights = {
            "behavioral_score": 0.20, "graph_score": 0.15, "entity_score": 0.10,
            "temporal_score": 0.15, "document_score": 0.10, "offramp_score": 0.10,
            "heuristic_max": 0.20,
        }
        score = sum(meta_dict.get(k, 0) * w for k, w in weights.items())
        return float(np.clip(score, 0, 1))
