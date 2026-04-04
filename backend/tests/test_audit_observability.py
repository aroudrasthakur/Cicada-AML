"""Observability and correctness tests motivated by the AML pipeline audit."""
import networkx as nx
import numpy as np
import pytest

from app.ml.typology_taxonomy import (
    FAN_OUT,
    MANY_TO_ONE,
    PEEL,
    CIRCULAR,
    RECONSOLIDATION,
    infer_cluster_typology,
    structure_typology,
    heuristic_name_to_taxonomy,
)


# ------------------------------------------------------------------
# 1. Meta-model provenance: learned vs fallback
# ------------------------------------------------------------------

class TestMetaProvenance:
    """Verify that _run_meta_batch exposes which path was taken."""

    def test_fallback_provenance(self):
        from app.ml.infer_pipeline import InferencePipeline

        pipe = InferencePipeline()
        pipe.meta_model = None  # force fallback

        n = 3
        zeros = np.zeros(n)

        class _FakeFlags:
            has_entity_intel = False
            has_address_tags = False
            class coverage_tier:
                value = "tier0"

        h_matrix = np.zeros((n, 185), dtype=np.float32)
        h_results = [{"top_confidence": 0} for _ in range(n)]

        pipe._run_meta_batch(
            zeros, zeros, zeros, zeros, zeros, zeros,
            h_matrix, h_results, _FakeFlags(), {},
        )
        assert getattr(pipe, "_last_meta_provenance", None) == "fallback"


# ------------------------------------------------------------------
# 2. Typology correctness on synthetic graphs
# ------------------------------------------------------------------

class TestTypologyCorrectness:
    """Ensure structure_typology and infer_cluster_typology assign the right labels."""

    def test_fan_out_small(self):
        G = nx.DiGraph()
        for i in range(6):
            G.add_edge("hub", f"d{i}")
        assert structure_typology(G) == FAN_OUT

    def test_many_to_one_small(self):
        G = nx.DiGraph()
        for i in range(6):
            G.add_edge(f"s{i}", "sink")
        assert structure_typology(G) == MANY_TO_ONE

    def test_linear_chain_is_peel(self):
        G = nx.DiGraph()
        for i in range(5):
            G.add_edge(f"n{i}", f"n{i+1}")
        assert structure_typology(G) == PEEL

    def test_cycle_detected(self):
        G = nx.DiGraph()
        G.add_edge("a", "b")
        G.add_edge("b", "c")
        G.add_edge("c", "a")
        assert structure_typology(G) == CIRCULAR

    def test_reconsolidation(self):
        G = nx.DiGraph()
        G.add_edge("src", "a")
        G.add_edge("src", "b")
        G.add_edge("a", "sink")
        G.add_edge("b", "sink")
        G.add_edge("a", "x")
        G.add_edge("b", "y")
        assert structure_typology(G) == RECONSOLIDATION

    def test_infer_prefers_ground_truth(self):
        G = nx.DiGraph()
        G.add_edge("a", "b")
        txs = [{"sender_wallet": "a", "receiver_wallet": "b", "typology": "fan-out dispersal"}]
        assert infer_cluster_typology(G, transactions=txs) == FAN_OUT


# ------------------------------------------------------------------
# 3. Heuristic top-K ranking visibility
# ------------------------------------------------------------------

class TestHeuristicTopK:
    """Verify top_k_triggers is populated and ranked."""

    def test_top_k_in_output(self):
        from app.ml.heuristics.runner import run_all

        result = run_all(
            tx={"transaction_id": "t1", "amount": 100},
            wallet={"address": "w1"},
            graph=None,
            features={},
            context={},
        )
        assert "top_k_triggers" in result
        assert isinstance(result["top_k_triggers"], list)
        if len(result["top_k_triggers"]) > 1:
            confs = [t["confidence"] for t in result["top_k_triggers"]]
            assert confs == sorted(confs, reverse=True), "top_k must be descending"


# ------------------------------------------------------------------
# 4. Explanation faithfulness vs contributing signals
# ------------------------------------------------------------------

class TestExplanationFaithfulness:
    """Check that explanation audit catches unmapped typology names."""

    def test_mapped_typology_no_warning(self):
        from app.ml.explainers import generate_explanation_with_audit

        result = generate_explanation_with_audit(
            heuristic_results={
                "triggered_count": 1,
                "top_typology": "PeelChain",
                "top_confidence": 0.8,
            },
            lens_scores={"behavioral_score": 0.6},
            meta_score=0.7,
        )
        assert result["_audit"]["taxonomy_mapping_failed"] is False
        assert result["_audit"]["top_typology_mapped"] == "peel chain"

    def test_unmapped_typology_flagged(self):
        from app.ml.explainers import generate_explanation_with_audit

        result = generate_explanation_with_audit(
            heuristic_results={
                "triggered_count": 1,
                "top_typology": "SomeUnknownHeuristic",
                "top_confidence": 0.5,
            },
            lens_scores={},
            meta_score=0.3,
        )
        assert result["_audit"]["taxonomy_mapping_failed"] is True

    def test_heuristic_name_to_taxonomy_coverage(self):
        known = [
            "PeelChain", "FanOutDispersal", "FanInAggregation",
            "ConsolidationAfterObfuscation", "CrossWalletChainLoops",
            "SelfTransferChain", "OTCBrokerLayering",
        ]
        for name in known:
            assert heuristic_name_to_taxonomy(name) is not None, f"{name} not mapped"
