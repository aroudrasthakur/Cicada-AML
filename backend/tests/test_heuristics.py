"""Tests for the 185-heuristic engine: registry, runner, individual results."""
import pytest
from unittest.mock import patch, MagicMock

from app.ml.heuristics.base import (
    BaseHeuristic,
    HeuristicResult,
    Applicability,
    Environment,
)
from app.ml.heuristics import registry
from app.ml.heuristics.runner import run_all, TOTAL_HEURISTICS


def _ensure_registry_populated():
    """Force-import all heuristic modules so _REGISTRY is populated."""
    import app.ml.heuristics.traditional  # noqa: F401
    import app.ml.heuristics.blockchain  # noqa: F401
    import app.ml.heuristics.hybrid  # noqa: F401
    import app.ml.heuristics.ai_enabled  # noqa: F401


class TestRegistryEntries:
    def test_at_least_100_heuristics_registered(self):
        _ensure_registry_populated()
        all_h = registry.get_all()
        assert len(all_h) > 100, f"Only {len(all_h)} heuristics registered, expected >100"

    def test_all_185_registered(self):
        _ensure_registry_populated()
        all_h = registry.get_all()
        assert len(all_h) == 185, f"Expected 185, got {len(all_h)}"

    def test_ids_are_in_valid_range(self):
        _ensure_registry_populated()
        all_h = registry.get_all()
        for hid in all_h:
            assert 1 <= hid <= 185

    def test_registry_entries_api_format(self):
        _ensure_registry_populated()
        entries = registry.get_registry_entries()
        assert isinstance(entries, list)
        if entries:
            entry = entries[0]
            assert "id" in entry
            assert "name" in entry
            assert "environment" in entry


class TestHeuristicRunner:
    def test_run_all_returns_correct_structure(self):
        _ensure_registry_populated()
        result = run_all(tx={"amount": 100}, context={})
        expected_keys = {
            "heuristic_vector",
            "applicability_vector",
            "triggered_ids",
            "triggered_count",
            "top_typology",
            "top_confidence",
            "explanations",
        }
        assert expected_keys == set(result.keys())

    def test_vector_length_matches_total(self):
        _ensure_registry_populated()
        result = run_all()
        assert len(result["heuristic_vector"]) == TOTAL_HEURISTICS
        assert len(result["applicability_vector"]) == TOTAL_HEURISTICS

    def test_triggered_count_matches_ids(self):
        _ensure_registry_populated()
        result = run_all(tx={"amount": 100})
        assert result["triggered_count"] == len(result["triggered_ids"])


class TestIndividualHeuristicResult:
    def test_single_heuristic_returns_valid_result(self):
        _ensure_registry_populated()
        all_h = registry.get_all()
        h = next(iter(all_h.values()))
        result = h.evaluate(tx={"amount": 100}, context={})
        assert isinstance(result, HeuristicResult)
        assert isinstance(result.triggered, bool)
        assert isinstance(result.confidence, float)
        assert isinstance(result.applicability, Applicability)


class TestApplicabilityOnMissingData:
    def test_inapplicable_when_required_data_missing(self):
        _ensure_registry_populated()
        all_h = registry.get_all()
        found_inapplicable = False
        for h in all_h.values():
            if h.data_requirements:
                status = h.check_data_requirements(context=None)
                if status == Applicability.INAPPLICABLE_MISSING_DATA:
                    found_inapplicable = True
                    break
        assert found_inapplicable, "Expected at least one heuristic to be inapplicable with no context"


class TestNoDuplicateIds:
    def test_no_duplicate_heuristic_ids(self):
        _ensure_registry_populated()
        all_h = registry.get_all()
        ids = list(all_h.keys())
        assert len(ids) == len(set(ids)), "Duplicate heuristic IDs found"
