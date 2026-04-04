"""End-to-end inference pipeline: heuristics-first, then ML lenses, then meta-learner."""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import joblib
import networkx as nx
import numpy as np
import pandas as pd
import torch

from app.config import settings
from app.ml.heuristics.runner import run_all as run_heuristics
from app.ml.platt_calibrator import ensure_platt_sigmoid_calibrator_on_main
from app.ml.lenses.behavioral_model import BehavioralLens
from app.ml.lenses.entity_model import EntityLens
from app.ml.lenses.graph_model import GraphLens
from app.ml.lenses.offramp_model import OfframpLens
from app.ml.lenses.temporal_model import TemporalLens
from app.ml.ml_device import xgb_predict_proba, resolve_torch_device
from app.services.data_availability_service import assess_data_availability
from app.services.feature_service import compute_all_features
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InferencePipeline:
    """Orchestrates the full Aegis-AML scoring pipeline.

    Ordering contract:
        1. Feature extraction (batched)
        2. Heuristics (per-tx, inherently sequential)
        3. Batch lenses: behavioral, graph, temporal, offramp, entity
        4. Batch meta-learner on stacked scores
        5. Threshold decision (vectorised)
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
        """Build a per-wallet summary dict used by heuristics."""
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
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Full pipeline — batched where possible, GPU-accelerated.

        1. Batch feature extraction
        2. Per-tx heuristics (inherently sequential)
        3. Batch lens inference (single XGBoost/PyTorch call per lens)
        4. Batch meta-learner
        5. Vectorised threshold decision
        """
        if not self._loaded:
            self.load_models()

        context = context or {}
        n_tx = len(transactions)

        if graph is None:
            from app.services.graph_service import build_wallet_graph
            graph = build_wallet_graph(transactions)
            logger.info("Built graph from transactions: %d nodes, %d edges",
                        graph.number_of_nodes(), graph.number_of_edges())

        # --- 0. Pre-compute wallet profiles for heuristics ---
        wallet_profiles = self._build_wallet_profiles(transactions, graph)
        logger.info("Built wallet profiles for %d addresses", len(wallet_profiles))

        # --- 1. Batch feature extraction ---
        nn = graph.number_of_nodes() if graph is not None else 0
        gm: Literal["full", "none"] = "full"
        skip_above = settings.infer_skip_graph_global_metrics_above_nodes
        if skip_above > 0 and nn > skip_above:
            gm = "none"
            logger.warning(
                "Inference: %d graph nodes (threshold %d); skipping global centralities for speed",
                nn, skip_above,
            )

        if progress_callback is not None:
            try:
                progress_callback({
                    "phase": "batch_features",
                    "tx_total": n_tx,
                    "graph_nodes": nn,
                    "global_metrics": gm,
                })
            except Exception:
                logger.exception("progress_callback failed")

        all_features = compute_all_features(transactions, graph, global_metrics=gm)
        combined = all_features["combined"]
        node_features = all_features.get("node_features") or {}

        data_flags = assess_data_availability(
            has_transactions=n_tx > 0,
            has_address_tags=context.get("has_address_tags", False),
            has_entity_links=context.get("has_entity_links", False),
        )

        lens_available: dict[str, bool] = {
            "behavioral": self.behavioral.xgb_model is not None,
            "graph": self.graph.model is not None,
            "temporal": self.temporal.model is not None,
            "offramp": self.offramp.classifier is not None,
            "entity": self.entity.classifier is not None,
        }

        # --- 2. Per-tx heuristics (sequential, but no ML overhead) ---
        if progress_callback is not None:
            try:
                progress_callback({"phase": "heuristics", "tx_total": n_tx})
            except Exception:
                logger.exception("progress_callback failed")

        h_results: list[dict] = []
        h_matrix = np.zeros((n_tx, 185), dtype=np.float32)
        feat_dicts: list[dict] = []
        wallet_ids: list[str] = []

        for i, tx in enumerate(transactions):
            row_features = combined.iloc[[i]] if i < len(combined) else pd.DataFrame()
            feat_dict = row_features.to_dict("records")[0] if not row_features.empty else {}
            feat_dicts.append(feat_dict)

            wallet_id = str(tx.get("sender_wallet") or tx.get("sender", ""))
            wallet_ids.append(wallet_id)
            wallet_prof = wallet_profiles.get(wallet_id, {"address": wallet_id})
            tx_ctx = self._build_tx_context(tx, wallet_prof, context)

            h_result = run_heuristics(
                tx=tx, wallet=wallet_prof, graph=graph,
                features=feat_dict, context=tx_ctx,
            )
            h_results.append(h_result)
            h_matrix[i] = h_result["heuristic_vector"]

        logger.info("Heuristics complete for %d transactions", n_tx)

        # --- 3. BATCH lens inference (single call per lens) ---
        if progress_callback is not None:
            try:
                progress_callback({"phase": "batch_lenses", "tx_total": n_tx})
            except Exception:
                logger.exception("progress_callback failed")

        # 3a. Behavioral (XGBoost + Autoencoder) — full batch
        beh_out = self.behavioral.predict(combined, h_matrix)
        beh_scores = np.asarray(beh_out["behavioral_score"], dtype=np.float64).ravel()
        beh_anomaly = np.asarray(beh_out["behavioral_anomaly_score"], dtype=np.float64).ravel()
        if len(beh_scores) < n_tx:
            beh_scores = np.pad(beh_scores, (0, n_tx - len(beh_scores)))
            beh_anomaly = np.pad(beh_anomaly, (0, n_tx - len(beh_anomaly)))

        # 3b. Graph lens — single GAT forward pass for entire graph
        graph_out = self.graph.predict(graph, node_features)
        graph_score_arr = graph_out["graph_score"]
        graph_embeddings = graph_out.get("embeddings")
        graph_node_mapping = graph_out.get("node_mapping", {})
        inv_node_map = {v: k for k, v in graph_node_mapping.items()} if graph_node_mapping else {}
        per_tx_graph_scores = np.zeros(n_tx, dtype=np.float64)
        for i, wid in enumerate(wallet_ids):
            node_idx = inv_node_map.get(wid)
            if node_idx is not None and node_idx < len(graph_score_arr):
                per_tx_graph_scores[i] = float(graph_score_arr[node_idx])

        # 3c. Temporal lens — batch all unique wallets
        unique_wallets = list(set(wallet_ids))
        temporal_out = self.temporal.predict(combined, unique_wallets)
        temporal_wallet_scores = temporal_out.get("temporal_scores", {})
        per_tx_temporal_scores = np.array(
            [temporal_wallet_scores.get(wid, 0.0) for wid in wallet_ids],
            dtype=np.float64,
        )

        # 3d. Offramp lens — full batch
        offramp_out = self.offramp.predict(combined, h_matrix)
        offramp_scores = np.asarray(offramp_out["offramp_score"], dtype=np.float64).ravel()
        if len(offramp_scores) < n_tx:
            offramp_scores = np.pad(offramp_scores, (0, n_tx - len(offramp_scores)))

        # 3e. Entity lens — single Louvain + XGBoost call for entire graph
        entity_out = self.entity.predict(
            graph,
            heuristic_scores={},
            embeddings=graph_embeddings,
            node_mapping=graph_node_mapping,
        )
        entity_wallet_scores = entity_out.get("entity_scores", {})
        per_tx_entity_scores = np.array(
            [entity_wallet_scores.get(wid, {}).get("entity_score", 0.0) for wid in wallet_ids],
            dtype=np.float64,
        )

        logger.info("All 5 lenses complete (batched)")

        # --- 4. Batch meta-learner ---
        if progress_callback is not None:
            try:
                progress_callback({"phase": "meta_learner", "tx_total": n_tx})
            except Exception:
                logger.exception("progress_callback failed")

        meta_scores = self._run_meta_batch(
            beh_scores, beh_anomaly, per_tx_graph_scores,
            per_tx_entity_scores, per_tx_temporal_scores, offramp_scores,
            h_matrix, h_results, data_flags, lens_available,
        )

        # --- 5. Vectorised threshold decision ---
        decision_threshold = self.threshold_config.get("decision_threshold", 0.5)
        high_threshold = self.threshold_config.get("high_risk_threshold", 0.9)
        low_ceiling = self.threshold_config.get("low_risk_ceiling", 0.3)
        meta_provenance = getattr(self, "_last_meta_provenance", "unknown")

        logger.info(
            "threshold_trace | decision=%.4f high=%.4f low_ceiling=%.4f provenance=%s",
            decision_threshold, high_threshold, low_ceiling, meta_provenance,
        )

        risk_levels = np.where(
            meta_scores >= high_threshold, "high",
            np.where(
                meta_scores >= decision_threshold, "medium",
                np.where(meta_scores <= low_ceiling, "low", "medium-low"),
            ),
        )

        # --- 6. Assemble results ---
        results: list[dict[str, Any]] = []
        for i, tx in enumerate(transactions):
            results.append({
                "transaction_id": tx.get("transaction_id") or tx.get("id", f"tx_{i}"),
                "meta_score": float(meta_scores[i]),
                "risk_level": str(risk_levels[i]),
                "meta_provenance": meta_provenance,
                "behavioral_score": float(beh_scores[i]),
                "behavioral_anomaly_score": float(beh_anomaly[i]),
                "graph_score": float(per_tx_graph_scores[i]),
                "entity_score": float(per_tx_entity_scores[i]),
                "temporal_score": float(per_tx_temporal_scores[i]),
                "offramp_score": float(offramp_scores[i]),
                "heuristic_vector": h_results[i]["heuristic_vector"],
                "applicability_vector": h_results[i]["applicability_vector"],
                "triggered_ids": h_results[i]["triggered_ids"],
                "heuristic_triggered_count": h_results[i]["triggered_count"],
                "heuristic_top_typology": h_results[i]["top_typology"],
                "heuristic_top_confidence": h_results[i]["top_confidence"],
                "heuristic_explanations": h_results[i]["explanations"],
                "coverage_tier": data_flags.coverage_tier.value,
                "decision_threshold": decision_threshold,
            })

            if progress_callback is not None:
                try:
                    progress_callback({"tx_index": i, "tx_total": n_tx})
                except Exception:
                    logger.exception("progress_callback failed")

        logger.info("Scored %d transactions", len(results))
        return results

    # ------------------------------------------------------------------
    # Batch meta-learner
    # ------------------------------------------------------------------

    def _run_meta_batch(
        self,
        beh_scores: np.ndarray,
        beh_anomaly: np.ndarray,
        graph_scores: np.ndarray,
        entity_scores: np.ndarray,
        temporal_scores: np.ndarray,
        offramp_scores: np.ndarray,
        h_matrix: np.ndarray,
        h_results: list[dict],
        data_flags: Any,
        lens_available: dict[str, bool],
    ) -> np.ndarray:
        """Vectorised meta-learner for all transactions at once."""
        n = len(beh_scores)

        h_nonzero_mask = h_matrix > 0
        h_means = np.where(
            h_nonzero_mask.any(axis=1),
            np.where(h_nonzero_mask, h_matrix, 0).sum(axis=1) / np.maximum(h_nonzero_mask.sum(axis=1), 1),
            0.0,
        )
        h_maxes = h_matrix.max(axis=1)
        h_triggered = h_nonzero_mask.sum(axis=1).astype(np.float32)
        h_top_conf = np.array([float(hr["top_confidence"] or 0) for hr in h_results], dtype=np.float32)
        h_ratio = h_triggered / max(h_matrix.shape[1], 1)
        n_lenses = float(sum(lens_available.values()))

        meta_dict_cols = {
            "behavioral_score": beh_scores,
            "behavioral_anomaly_score": beh_anomaly,
            "graph_score": graph_scores,
            "entity_score": entity_scores,
            "temporal_score": temporal_scores,
            "offramp_score": offramp_scores,
            "heuristic_mean": h_means,
            "heuristic_max": h_maxes,
            "heuristic_triggered_count": h_triggered,
            "heuristic_top_confidence": h_top_conf,
            "heuristic_triggered_ratio": h_ratio,
            "has_entity_intel": np.full(n, float(data_flags.has_entity_intel)),
            "has_address_tags": np.full(n, float(data_flags.has_address_tags)),
            "coverage_tier_0": np.full(n, float(data_flags.coverage_tier.value == "tier0")),
            "coverage_tier_1": np.full(n, float(data_flags.coverage_tier.value == "tier1")),
            "coverage_tier_2": np.full(n, float(data_flags.coverage_tier.value == "tier2")),
            "n_lenses_available": np.full(n, n_lenses),
        }

        if self.meta_model is not None:
            feature_order = self.meta_feature_names or list(meta_dict_cols.keys())
            X = np.column_stack([meta_dict_cols.get(f, np.zeros(n)) for f in feature_order]).astype(np.float32)
            proba = xgb_predict_proba(self.meta_model, X)
            scores = proba[:, 1].astype(np.float64)
            logger.info(
                "meta_provenance | method=learned_model features=%s "
                "mean_score=%.4f std_score=%.4f n=%d",
                feature_order, float(scores.mean()), float(scores.std()), n,
            )
            self._last_meta_provenance = "learned"
            return scores

        fallback_weights = {
            "behavioral_score": 0.225, "graph_score": 0.175, "entity_score": 0.125,
            "temporal_score": 0.175, "offramp_score": 0.125,
            "heuristic_max": 0.175,
        }
        score = np.zeros(n, dtype=np.float64)
        for k, w in fallback_weights.items():
            score += meta_dict_cols.get(k, np.zeros(n)) * w
        score = np.clip(score, 0, 1)
        logger.info(
            "meta_provenance | method=fallback_fusion weights=%s "
            "mean_score=%.4f std_score=%.4f n=%d",
            fallback_weights, float(score.mean()), float(score.std()), n,
        )
        self._last_meta_provenance = "fallback"
        return score
