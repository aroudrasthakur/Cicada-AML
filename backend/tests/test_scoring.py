"""Tests for the InferencePipeline scoring interface."""
import sys
import types
from unittest.mock import patch, MagicMock

import pytest
import numpy as np
import pandas as pd
import networkx as nx

# Stub torch_geometric if not installed so infer_pipeline can be imported
if "torch_geometric" not in sys.modules:
    _tg = types.ModuleType("torch_geometric")
    _tg_nn = types.ModuleType("torch_geometric.nn")
    _tg_data = types.ModuleType("torch_geometric.data")
    _tg_nn.GATConv = MagicMock()
    _tg_nn.GCNConv = MagicMock()

    class _FakeData:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    _tg_data.Data = _FakeData
    sys.modules["torch_geometric"] = _tg
    sys.modules["torch_geometric.nn"] = _tg_nn
    sys.modules["torch_geometric.data"] = _tg_data

from app.ml.infer_pipeline import InferencePipeline


class TestInferencePipelineStructure:
    def test_has_required_methods(self):
        pipeline = InferencePipeline()
        assert hasattr(pipeline, "load_models")
        assert hasattr(pipeline, "score_transactions")
        assert callable(pipeline.load_models)
        assert callable(pipeline.score_transactions)

    def test_has_all_lenses(self):
        pipeline = InferencePipeline()
        assert hasattr(pipeline, "behavioral")
        assert hasattr(pipeline, "graph")
        assert hasattr(pipeline, "entity")
        assert hasattr(pipeline, "temporal")
        assert hasattr(pipeline, "offramp")

    def test_initial_state(self):
        pipeline = InferencePipeline()
        assert pipeline._loaded is False
        assert pipeline.meta_model is None


class TestScoreTransactionsReturnsResults:
    @patch("app.ml.infer_pipeline.run_heuristics")
    @patch("app.ml.infer_pipeline.compute_all_features")
    @patch("app.ml.infer_pipeline.assess_data_availability")
    def test_output_format(
        self, mock_avail, mock_all_feat, mock_heur,
        sample_transactions, sample_graph,
    ):
        mock_all_feat.return_value = {
            "transaction_features": pd.DataFrame({"amount": [100.0]}),
            "graph_features": pd.DataFrame(),
            "subgraph_features": pd.DataFrame(),
            "combined": pd.DataFrame({"amount": [100.0] * len(sample_transactions)}),
            "node_features": {},
        }
        mock_heur.return_value = {
            "heuristic_vector": [0.0] * 185,
            "applicability_vector": ["applicable"] * 185,
            "triggered_ids": [],
            "triggered_count": 0,
            "top_typology": None,
            "top_confidence": None,
            "explanations": {},
        }

        from app.schemas.data_contract import DataAvailabilityFlags, CoverageTier
        mock_avail.return_value = DataAvailabilityFlags(
            has_entity_intel=False,
            has_address_tags=False,
            coverage_tier=CoverageTier.TIER0,
        )

        pipeline = InferencePipeline()
        pipeline._loaded = True

        results = pipeline.score_transactions(sample_transactions, sample_graph)

        assert isinstance(results, list)
        assert len(results) == len(sample_transactions)

        required_keys = {
            "transaction_id", "meta_score", "risk_level",
            "behavioral_score", "graph_score", "entity_score",
            "temporal_score", "offramp_score",
            "heuristic_triggered_count", "coverage_tier",
        }
        for r in results:
            assert required_keys.issubset(set(r.keys())), f"Missing keys: {required_keys - set(r.keys())}"
            assert 0 <= r["meta_score"] <= 1
            assert r["risk_level"] in {"high", "medium", "medium-low", "low"}
