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
from app.ml.platt_calibrator import ensure_platt_sigmoid_calibrator_on_main
from app.ml.lenses.behavioral_model import BehavioralLens
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
        3. Parallel lenses: behavioral, graph, temporal, offramp
        4. Entity lens (depends on graph embeddings from step 3)
        5. Meta-learner on stacked scores
        6. Threshold decision
    """

    def __init__(self) -> None:
        self.behavioral = BehavioralLens()
        self.graph = GraphLens()
        self.entity = EntityLens()
        self.temporal = TemporalLens()
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
        self.offramp.load(settings.offramp_model_path)

        meta_path = Path(settings.meta_model_path)
        if meta_path.exists():
            ensure_platt_sigmoid_calibrator_on_main()
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

    # ------------------------------------------------------------------
    # Batch-level pre-computation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_wallet_profiles(
        transactions: list[dict[str, Any]],
        graph: nx.DiGraph,
    ) -> dict[str, dict[str, Any]]:
        """Build a per-wallet summary dict used by heuristics.

        Each entry has the shape expected by heuristic ``wallet`` param:
        ``{"address": str, "total_in": float, "total_out": float, ...}``
        """
        profiles: dict[str, dict[str, Any]] = {}

        for tx in transactions:
            sender = str(tx.get("sender_wallet") or tx.get("sender", ""))
            receiver = str(tx.get("receiver_wallet") or tx.get("receiver", ""))
            amount = float(tx.get("amount", 0))
            ts = tx.get("timestamp", "")

            for addr in (sender, receiver):
                if not addr:
                    continue
                if addr not in profiles:
                    profiles[addr] = {
                        "address": addr,
                        "total_in": 0.0,
                        "total_out": 0.0,
                        "tx_count": 0,
                        "amounts": [],
                        "timestamps": [],
                        "first_seen": ts,
                        "last_seen": ts,
                    }

            if sender:
                profiles[sender]["total_out"] += amount
                profiles[sender]["tx_count"] += 1
                profiles[sender]["amounts"].append(amount)
                profiles[sender]["timestamps"].append(ts)
                if ts and ts < profiles[sender]["first_seen"]:
                    profiles[sender]["first_seen"] = ts
                if ts and ts > profiles[sender]["last_seen"]:
                    profiles[sender]["last_seen"] = ts

            if receiver:
                profiles[receiver]["total_in"] += amount
                profiles[receiver]["tx_count"] += 1
                profiles[receiver]["amounts"].append(amount)
                profiles[receiver]["timestamps"].append(ts)
                if ts and ts < profiles[receiver]["first_seen"]:
                    profiles[receiver]["first_seen"] = ts
                if ts and ts > profiles[receiver]["last_seen"]:
                    profiles[receiver]["last_seen"] = ts

        for addr, p in profiles.items():
            if graph.has_node(addr):
                p["in_degree"] = graph.in_degree(addr)
                p["out_degree"] = graph.out_degree(addr)
            else:
                p["in_degree"] = 0
                p["out_degree"] = 0
            p["pass_through_ratio"] = (
                p["total_out"] / p["total_in"] if p["total_in"] > 0 else 0.0
            )
            # Approximate balance: what stays in the wallet
            p["balances"] = [max(p["total_in"] - p["total_out"], 0.0)]

        return profiles

    @staticmethod
    def _build_tx_context(
        tx: dict[str, Any],
        wallet_profile: dict[str, Any],
        global_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge global context with per-wallet data for heuristic evaluation."""
        ctx = dict(global_context)
        ctx["amount"] = wallet_profile.get("amounts", [])
        ctx["balances"] = wallet_profile.get("balances", [])
        ctx["timestamps"] = wallet_profile.get("timestamps", [])
        ctx["total_in"] = wallet_profile.get("total_in", 0)
        ctx["total_out"] = wallet_profile.get("total_out", 0)
        ctx["tx_count"] = wallet_profile.get("tx_count", 0)
        return ctx

    # ------------------------------------------------------------------

    def score_transactions(
        self,
        transactions: list[dict[str, Any]],
        graph: nx.DiGraph | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Full pipeline: features -> heuristics -> lenses -> meta -> threshold -> results."""
        if not self._loaded:
            self.load_models()

        context = context or {}

        if graph is None:
            from app.services.graph_service import build_wallet_graph
            graph = build_wallet_graph(transactions)
            logger.info("Built graph from transactions: %d nodes, %d edges",
                        graph.number_of_nodes(), graph.number_of_edges())

        # --- 0. Pre-compute wallet profiles for heuristics ---
        wallet_profiles = self._build_wallet_profiles(transactions, graph)
        logger.info("Built wallet profiles for %d addresses", len(wallet_profiles))

        # --- 1. Feature extraction ---
        all_features = compute_all_features(transactions, graph)
        tx_features = all_features["transaction_features"]
        combined = all_features["combined"]
        node_features = compute_node_features(graph) if graph.number_of_nodes() > 0 else {}

        data_flags = assess_data_availability(
            has_transactions=len(transactions) > 0,
            has_address_tags=context.get("has_address_tags", False),
            has_entity_links=context.get("has_entity_links", False),
        )

        results = []
        for i, tx in enumerate(transactions):
            row_features = combined.iloc[[i]] if i < len(combined) else pd.DataFrame()
            feat_dict = row_features.to_dict("records")[0] if not row_features.empty else {}

            # --- 2. Heuristics (always first) ---
            wallet_id = str(tx.get("sender_wallet") or tx.get("sender", ""))
            wallet_prof = wallet_profiles.get(wallet_id, {"address": wallet_id})
            tx_ctx = self._build_tx_context(tx, wallet_prof, context)

            h_result = run_heuristics(
                tx=tx,
                wallet=wallet_prof,
                graph=graph,
                features=feat_dict,
                context=tx_ctx,
            )
            h_vec = np.array(h_result["heuristic_vector"], dtype=np.float32)

            # --- 3. Parallel lens group: behavioral, graph, temporal, offramp ---
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
        lens_available: dict[str, bool] = {
            "behavioral": self.behavioral.xgb_model is not None,
            "graph": self.graph.model is not None,
            "temporal": self.temporal.model is not None,
            "offramp": self.offramp.classifier is not None,
            "entity": self.entity.classifier is not None,
        }
        scores["_lens_available"] = lens_available

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

        def _offramp() -> None:
            out = self.offramp.predict(row_features if not row_features.empty else pd.DataFrame(), h_vec)
            scores["offramp_score"] = float(np.mean(out["offramp_score"]))

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(_behavioral),
                pool.submit(_graph),
                pool.submit(_temporal),
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
            "offramp_score": lens_scores.get("offramp_score", 0),
            "heuristic_mean": float(h_nonzero.mean()) if len(h_nonzero) > 0 else 0.0,
            "heuristic_max": float(h_vec.max()),
            "heuristic_triggered_count": triggered,
            "heuristic_top_confidence": float(h_result["top_confidence"] or 0),
            "heuristic_triggered_ratio": triggered / max(len(h_vec), 1),
            "has_entity_intel": float(data_flags.has_entity_intel),
            "has_address_tags": float(data_flags.has_address_tags),
            "coverage_tier_0": float(data_flags.coverage_tier.value == "tier0"),
            "coverage_tier_1": float(data_flags.coverage_tier.value == "tier1"),
            "coverage_tier_2": float(data_flags.coverage_tier.value == "tier2"),
            "n_lenses_available": sum(
                lens_scores.get("_lens_available", {}).values()
            ),
        }

        if self.meta_model is not None:
            feature_order = self.meta_feature_names or list(meta_dict.keys())
            X = np.array([[meta_dict.get(f, 0.0) for f in feature_order]], dtype=np.float32)
            return float(self.meta_model.predict_proba(X)[0, 1])

        # Fallback: weighted average when meta-model is not trained yet
        weights = {
            "behavioral_score": 0.225, "graph_score": 0.175, "entity_score": 0.125,
            "temporal_score": 0.175, "offramp_score": 0.125,
            "heuristic_max": 0.175,
        }
        score = sum(meta_dict.get(k, 0) * w for k, w in weights.items())
        return float(np.clip(score, 0, 1))
