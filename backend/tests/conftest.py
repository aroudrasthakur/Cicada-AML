"""Shared pytest fixtures for Aegis-AML backend tests."""
import pytest
import numpy as np
import pandas as pd
import networkx as nx


@pytest.fixture
def sample_transactions():
    """Five realistic transaction dicts with all required fields."""
    base_ts = pd.Timestamp("2024-06-01T12:00:00Z")
    return [
        {
            "transaction_id": "tx_001",
            "tx_hash": "0xabc001",
            "sender_wallet": "wallet_A",
            "receiver_wallet": "wallet_B",
            "amount": 1500.00,
            "asset_type": "USDT",
            "chain_id": "ethereum",
            "timestamp": (base_ts + pd.Timedelta(minutes=0)).isoformat(),
            "fee": 2.50,
            "label": "illicit",
            "label_source": "manual",
        },
        {
            "transaction_id": "tx_002",
            "tx_hash": "0xabc002",
            "sender_wallet": "wallet_B",
            "receiver_wallet": "wallet_C",
            "amount": 750.00,
            "asset_type": "USDT",
            "chain_id": "ethereum",
            "timestamp": (base_ts + pd.Timedelta(minutes=5)).isoformat(),
            "fee": 1.20,
            "label": None,
            "label_source": None,
        },
        {
            "transaction_id": "tx_003",
            "tx_hash": "0xabc003",
            "sender_wallet": "wallet_A",
            "receiver_wallet": "wallet_D",
            "amount": 3200.00,
            "asset_type": "ETH",
            "chain_id": "ethereum",
            "timestamp": (base_ts + pd.Timedelta(minutes=10)).isoformat(),
            "fee": 5.00,
            "label": "licit",
            "label_source": "manual",
        },
        {
            "transaction_id": "tx_004",
            "tx_hash": "0xabc004",
            "sender_wallet": "wallet_C",
            "receiver_wallet": "wallet_E",
            "amount": 500.00,
            "asset_type": "USDT",
            "chain_id": "ethereum",
            "timestamp": (base_ts + pd.Timedelta(minutes=15)).isoformat(),
            "fee": 0.80,
            "label": "illicit",
            "label_source": "elliptic",
        },
        {
            "transaction_id": "tx_005",
            "tx_hash": "0xabc005",
            "sender_wallet": "wallet_D",
            "receiver_wallet": "wallet_A",
            "amount": 100.00,
            "asset_type": "BTC",
            "chain_id": "bitcoin",
            "timestamp": (base_ts + pd.Timedelta(minutes=20)).isoformat(),
            "fee": 0.10,
            "label": None,
            "label_source": None,
        },
    ]


@pytest.fixture
def sample_wallets():
    """Three wallet dicts matching the shape of _extract_wallets output."""
    return [
        {
            "wallet_address": "wallet_A",
            "first_seen": "2024-06-01T12:00:00+00:00",
            "last_seen": "2024-06-01T12:20:00+00:00",
            "total_in": 100.00,
            "total_out": 4700.00,
        },
        {
            "wallet_address": "wallet_B",
            "first_seen": "2024-06-01T12:00:00+00:00",
            "last_seen": "2024-06-01T12:05:00+00:00",
            "total_in": 1500.00,
            "total_out": 750.00,
        },
        {
            "wallet_address": "wallet_C",
            "first_seen": "2024-06-01T12:05:00+00:00",
            "last_seen": "2024-06-01T12:15:00+00:00",
            "total_in": 750.00,
            "total_out": 500.00,
        },
    ]


@pytest.fixture
def sample_graph():
    """Simple DiGraph: 5 nodes, 7 edges including a cycle A->B->C->A."""
    G = nx.DiGraph()
    edges = [
        ("wallet_A", "wallet_B", {"amount": 1500.0, "timestamp": "2024-06-01T12:00:00Z"}),
        ("wallet_B", "wallet_C", {"amount": 750.0, "timestamp": "2024-06-01T12:05:00Z"}),
        ("wallet_A", "wallet_D", {"amount": 3200.0, "timestamp": "2024-06-01T12:10:00Z"}),
        ("wallet_C", "wallet_E", {"amount": 500.0, "timestamp": "2024-06-01T12:15:00Z"}),
        ("wallet_D", "wallet_A", {"amount": 100.0, "timestamp": "2024-06-01T12:20:00Z"}),
        ("wallet_C", "wallet_A", {"amount": 200.0, "timestamp": "2024-06-01T12:25:00Z"}),
        ("wallet_E", "wallet_B", {"amount": 50.0, "timestamp": "2024-06-01T12:30:00Z"}),
    ]
    G.add_edges_from([(u, v, d) for u, v, d in edges])
    return G


@pytest.fixture
def sample_features():
    """Dict of computed features mimicking compute_all_features output."""
    wallets = ["wallet_A", "wallet_B", "wallet_C", "wallet_D", "wallet_E"]
    tx_feats = pd.DataFrame({
        "transaction_id": ["tx_001", "tx_002", "tx_003", "tx_004", "tx_005"],
        "sender_wallet": ["wallet_A", "wallet_B", "wallet_A", "wallet_C", "wallet_D"],
        "receiver_wallet": ["wallet_B", "wallet_C", "wallet_D", "wallet_E", "wallet_A"],
        "amount": [1500.0, 750.0, 3200.0, 500.0, 100.0],
        "log_amount": np.log1p([1500.0, 750.0, 3200.0, 500.0, 100.0]),
        "fee_ratio": [0.0017, 0.0016, 0.0016, 0.0016, 0.0010],
        "is_round_amount": [True, True, True, True, True],
        "sender_tx_count": [2, 1, 2, 1, 1],
        "receiver_tx_count": [1, 1, 1, 1, 1],
    })
    graph_feats = pd.DataFrame({
        "in_degree": [1, 2, 1, 1, 1],
        "out_degree": [2, 1, 2, 1, 0],
        "pagerank": [0.25, 0.20, 0.20, 0.18, 0.17],
        "betweenness": [0.3, 0.2, 0.25, 0.1, 0.0],
    }, index=wallets)
    return {
        "transaction_features": tx_feats,
        "graph_features": graph_feats,
        "subgraph_features": pd.DataFrame(index=wallets),
        "combined": tx_feats,
    }
