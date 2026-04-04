"""Tests for the 6 ML lens predict() interfaces (no trained models loaded)."""
import sys
import types
from unittest.mock import MagicMock

import pytest
import numpy as np
import pandas as pd
import networkx as nx

# Stub torch_geometric if not installed so graph_model can be imported
if "torch_geometric" not in sys.modules:
    _tg = types.ModuleType("torch_geometric")
    _tg_nn = types.ModuleType("torch_geometric.nn")
    _tg_data = types.ModuleType("torch_geometric.data")

    class _FakeGATConv(MagicMock):
        pass

    class _FakeData:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    _tg_nn.GATConv = _FakeGATConv
    _tg_data.Data = _FakeData
    sys.modules["torch_geometric"] = _tg
    sys.modules["torch_geometric.nn"] = _tg_nn
    sys.modules["torch_geometric.data"] = _tg_data

from app.ml.lenses.behavioral_model import BehavioralLens
from app.ml.lenses.graph_model import GraphLens
from app.ml.lenses.entity_model import EntityLens
from app.ml.lenses.temporal_model import TemporalLens
from app.ml.lenses.document_model import DocumentLens
from app.ml.lenses.offramp_model import OfframpLens


@pytest.fixture
def feature_df():
    return pd.DataFrame({
        "amount": [1500.0, 750.0, 3200.0],
        "log_amount": np.log1p([1500.0, 750.0, 3200.0]),
        "fee_ratio": [0.002, 0.001, 0.003],
        "is_round_amount": [True, True, True],
        "burstiness_score": [0.5, 0.1, 0.8],
        "sender_tx_count": [3, 1, 2],
        "receiver_tx_count": [1, 2, 1],
        "balance_ratio": [0.3, -0.1, 0.5],
        "fan_in_ratio": [0.3, 0.5, 0.2],
        "weighted_in": [100.0, 200.0, 50.0],
        "in_degree": [2, 3, 1],
        "relay_pattern_score": [0.4, 0.1, 0.7],
        "unique_counterparties": [3, 2, 4],
        "amount_deviation": [0.1, 0.0, 0.5],
        "sender_repeat_count": [2, 1, 3],
        "suspicious_neighbor_ratio_1hop": [0.1, 0.2, 0.3],
        "suspicious_neighbor_ratio_2hop": [0.05, 0.1, 0.15],
    })


@pytest.fixture
def heuristic_vec():
    return np.random.rand(185).astype(np.float32)


class TestBehavioralLensPredict:
    def test_returns_expected_keys(self, feature_df, heuristic_vec):
        lens = BehavioralLens()
        result = lens.predict(feature_df, heuristic_vec)
        assert "behavioral_score" in result
        assert "behavioral_anomaly_score" in result

    def test_score_shapes(self, feature_df, heuristic_vec):
        lens = BehavioralLens()
        result = lens.predict(feature_df, heuristic_vec)
        assert len(result["behavioral_score"]) == len(feature_df)
        assert len(result["behavioral_anomaly_score"]) == len(feature_df)


class TestGraphLensPredict:
    def test_returns_expected_keys(self, sample_graph):
        lens = GraphLens()
        node_features = {
            n: {"in_degree": 1, "out_degree": 1, "weighted_in": 10, "weighted_out": 10,
                "betweenness_centrality": 0.1, "pagerank": 0.2, "clustering_coefficient": 0.1}
            for n in sample_graph.nodes()
        }
        result = lens.predict(sample_graph, node_features)
        assert "graph_score" in result
        assert "embeddings" in result

    def test_score_length_matches_nodes(self, sample_graph):
        lens = GraphLens()
        node_features = {n: {"in_degree": 1, "out_degree": 1, "weighted_in": 0,
                             "weighted_out": 0, "betweenness_centrality": 0,
                             "pagerank": 0, "clustering_coefficient": 0}
                         for n in sample_graph.nodes()}
        result = lens.predict(sample_graph, node_features)
        assert len(result["graph_score"]) == sample_graph.number_of_nodes()


class TestEntityLensPredict:
    def test_returns_expected_keys(self, sample_graph):
        lens = EntityLens()
        result = lens.predict(sample_graph)
        assert "entity_scores" in result
        assert "partition" in result

    def test_entity_scores_for_all_nodes(self, sample_graph):
        lens = EntityLens()
        result = lens.predict(sample_graph)
        for node in sample_graph.nodes():
            assert node in result["entity_scores"]


class TestTemporalLensPredict:
    def test_returns_temporal_scores_dict(self, sample_transactions):
        lens = TemporalLens()
        df = pd.DataFrame(sample_transactions)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        wallets = ["wallet_A", "wallet_B"]
        result = lens.predict(df, wallets)
        assert "temporal_scores" in result
        assert isinstance(result["temporal_scores"], dict)

    def test_scores_for_requested_wallets(self, sample_transactions):
        lens = TemporalLens()
        df = pd.DataFrame(sample_transactions)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        wallets = ["wallet_A", "wallet_C"]
        result = lens.predict(df, wallets)
        for w in wallets:
            assert w in result["temporal_scores"]


class TestDocumentLensPredict:
    def test_returns_expected_keys(self, feature_df, heuristic_vec):
        lens = DocumentLens()
        result = lens.predict(feature_df, heuristic_vec)
        assert "document_score" in result
        assert "document_lens_mode" in result

    def test_limited_mode_without_documents(self, feature_df):
        lens = DocumentLens()
        result = lens.predict(feature_df)
        assert result["document_lens_mode"] == "limited"


class TestOfframpLensPredict:
    def test_returns_expected_keys(self, feature_df, heuristic_vec):
        lens = OfframpLens()
        result = lens.predict(feature_df, heuristic_vec)
        assert "offramp_score" in result

    def test_score_length(self, feature_df):
        lens = OfframpLens()
        result = lens.predict(feature_df)
        assert len(result["offramp_score"]) == len(feature_df)
