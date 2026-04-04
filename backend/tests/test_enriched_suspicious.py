"""Tests for merging suspicious txns with run_transactions and run_scores."""
import json

from app.repositories import runs_repo


def test_parse_triggered_ids():
    assert runs_repo._parse_triggered_ids(None) == []
    assert runs_repo._parse_triggered_ids([]) == []
    assert runs_repo._parse_triggered_ids([91, 92]) == [91, 92]
    assert runs_repo._parse_triggered_ids(json.dumps([1, 2, 3])) == [1, 2, 3]
    assert runs_repo._parse_triggered_ids("not json") == []
    assert runs_repo._parse_triggered_ids("   ") == []


def test_heuristic_labels_for_ids_resolves_registry():
    labels = runs_repo._heuristic_labels_for_ids([1, 91])
    assert len(labels) == 2
    assert all(isinstance(x, str) and len(x) > 0 for x in labels)


def test_triggered_ids_for_storage_unions_vector_and_ids():
    from app.services import pipeline_run_service as prs

    hv = [0.0] * 185
    hv[4] = 0.42  # id 5
    r = {"triggered_ids": [1], "heuristic_vector": hv}
    ids = prs._triggered_ids_for_storage(r)
    assert ids == [1, 5]

    r2 = {"triggered_ids": [], "heuristic_vector": hv}
    assert prs._triggered_ids_for_storage(r2) == [5]
