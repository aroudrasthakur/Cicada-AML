"""Tests for graph construction and utilities."""
import pytest
import networkx as nx

from app.services.graph_service import (
    build_wallet_graph,
    compute_node_features,
    get_subgraph_for_wallet,
)
from app.utils.graph_utils import graph_to_cytoscape


class TestBuildWalletGraph:
    def test_correct_nodes_and_edges(self, sample_transactions):
        G = build_wallet_graph(sample_transactions)
        assert isinstance(G, nx.DiGraph)
        assert G.number_of_nodes() == 5
        assert G.number_of_edges() >= 4

    def test_empty_input_returns_empty_graph(self):
        G = build_wallet_graph([])
        assert G.number_of_nodes() == 0
        assert G.number_of_edges() == 0

    def test_self_loop_ignored(self):
        txs = [{"transaction_id": "t1", "sender_wallet": "w_A", "receiver_wallet": "w_A", "amount": 10}]
        G = build_wallet_graph(txs)
        assert G.number_of_nodes() == 0

    def test_edge_attributes_present(self, sample_transactions):
        G = build_wallet_graph(sample_transactions)
        for u, v, data in G.edges(data=True):
            assert "amount" in data
            assert "timestamp" in data


class TestComputeNodeFeatures:
    def test_features_for_all_nodes(self, sample_graph):
        features = compute_node_features(sample_graph)
        assert len(features) == sample_graph.number_of_nodes()

    def test_expected_keys_per_node(self, sample_graph):
        features = compute_node_features(sample_graph)
        expected_keys = {
            "in_degree", "out_degree", "weighted_in", "weighted_out",
            "total_volume", "balance_ratio",
            "betweenness_centrality", "pagerank", "clustering_coefficient",
        }
        for node, feat_dict in features.items():
            assert expected_keys.issubset(feat_dict.keys()), f"Missing keys for {node}"

    def test_empty_graph(self):
        G = nx.DiGraph()
        assert compute_node_features(G) == {}


class TestKHopSubgraph:
    def test_one_hop_subgraph_size(self, sample_graph):
        sub = get_subgraph_for_wallet(sample_graph, "wallet_A", hops=1)
        assert sub.number_of_nodes() >= 2
        assert "wallet_A" in sub.nodes()

    def test_zero_hops_returns_only_seed(self, sample_graph):
        sub = get_subgraph_for_wallet(sample_graph, "wallet_E", hops=0)
        assert sub.number_of_nodes() == 1

    def test_missing_wallet_returns_empty(self, sample_graph):
        sub = get_subgraph_for_wallet(sample_graph, "nonexistent", hops=2)
        assert sub.number_of_nodes() == 0


class TestGraphToCytoscape:
    def test_output_format(self, sample_graph):
        result = graph_to_cytoscape(sample_graph)
        assert "elements" in result
        elements = result["elements"]
        node_els = [e for e in elements if "source" not in e["data"]]
        edge_els = [e for e in elements if "source" in e["data"]]
        assert len(node_els) == sample_graph.number_of_nodes()
        assert len(edge_els) == sample_graph.number_of_edges()

    def test_node_element_has_id(self, sample_graph):
        result = graph_to_cytoscape(sample_graph)
        for el in result["elements"]:
            assert "id" in el["data"] or "source" in el["data"]
