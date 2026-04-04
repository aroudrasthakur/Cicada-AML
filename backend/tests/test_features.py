"""Tests for feature extraction pipelines."""
import pytest
import pandas as pd
import numpy as np
import networkx as nx

from app.ml.transaction_features import compute_transaction_features
from app.ml.graph_features import compute_graph_features
from app.ml.subgraph_features import compute_subgraph_features
from app.services.feature_service import compute_all_features
from app.services.graph_service import compute_node_features


class TestTransactionFeatures:
    def test_adds_expected_columns(self, sample_transactions):
        df = pd.DataFrame(sample_transactions)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        result = compute_transaction_features(df)

        expected_cols = [
            "log_amount", "is_round_amount", "fee_ratio",
            "sender_tx_count", "receiver_tx_count",
            "time_since_prev_out", "time_since_prev_in",
            "sender_repeat_count", "burstiness_score", "amount_deviation",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_returns_same_row_count(self, sample_transactions):
        df = pd.DataFrame(sample_transactions)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        result = compute_transaction_features(df)
        assert len(result) == len(df)

    def test_empty_dataframe_returns_empty(self):
        result = compute_transaction_features(pd.DataFrame())
        assert result.empty


class TestGraphFeatures:
    def test_returns_expected_columns(self, sample_graph):
        node_feats = compute_node_features(sample_graph)
        result = compute_graph_features(sample_graph, node_feats)

        expected_cols = [
            "in_degree", "out_degree", "weighted_in", "weighted_out",
            "fan_in_ratio", "fan_out_ratio", "unique_counterparties",
            "betweenness", "pagerank", "clustering_coeff",
            "suspicious_neighbor_ratio_1hop", "suspicious_neighbor_ratio_2hop",
            "relay_pattern_score",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_returns_row_per_node(self, sample_graph):
        node_feats = compute_node_features(sample_graph)
        result = compute_graph_features(sample_graph, node_feats)
        assert len(result) == sample_graph.number_of_nodes()


class TestSubgraphFeatures:
    def test_computes_without_error(self, sample_graph, sample_transactions):
        df = pd.DataFrame(sample_transactions)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        result = compute_subgraph_features(sample_graph, df)
        assert isinstance(result, pd.DataFrame)


class TestFeatureService:
    def test_compute_all_features_returns_all_keys(self, sample_transactions, sample_graph):
        result = compute_all_features(sample_transactions, sample_graph)
        expected_keys = {
            "transaction_features",
            "graph_features",
            "subgraph_features",
            "combined",
            "node_features",
        }
        assert set(result.keys()) == expected_keys

    def test_empty_graph_still_returns_keys(self, sample_transactions):
        empty_graph = nx.DiGraph()
        result = compute_all_features(sample_transactions, empty_graph)
        assert "transaction_features" in result
        assert "combined" in result
