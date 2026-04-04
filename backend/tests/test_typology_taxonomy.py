"""Tests for AML cluster typology inference (non–peel-chain patterns)."""
import networkx as nx

from app.ml.typology_taxonomy import (
    FAN_OUT,
    MANY_TO_ONE,
    PEEL,
    infer_cluster_typology,
    normalize_ground_truth_label,
    structure_typology,
)


def test_ground_truth_many_to_one():
    assert normalize_ground_truth_label("many-to-one collection") == MANY_TO_ONE
    assert normalize_ground_truth_label("Many to One") == MANY_TO_ONE


def test_structure_fan_out_small_graph():
    G = nx.DiGraph()
    hub = "h"
    for i in range(4):
        G.add_edge(hub, f"d{i}", amount=1.0)
    assert structure_typology(G) == FAN_OUT


def test_structure_peel_path():
    G = nx.DiGraph()
    for i in range(4):
        G.add_edge(f"a{i}", f"a{i + 1}", amount=1.0)
    assert structure_typology(G) == PEEL


def test_infer_respects_csv_typology():
    G = nx.DiGraph()
    G.add_edge("a", "b")
    txs = [{"sender_wallet": "a", "receiver_wallet": "b", "typology": "fan-out dispersal"}]
    t = infer_cluster_typology(G, transactions=txs, scoring_rows=[])
    assert t == FAN_OUT


def test_cross_chain_from_chain_ids():
    G = nx.DiGraph()
    G.add_edge("a", "b")
    txs = [
        {"sender_wallet": "a", "receiver_wallet": "b", "chain_id": "eth"},
        {"sender_wallet": "b", "receiver_wallet": "c", "chain_id": "btc"},
    ]
    from app.ml.typology_taxonomy import CROSS_CHAIN

    t = infer_cluster_typology(G, transactions=txs, scoring_rows=[])
    assert t == CROSS_CHAIN
