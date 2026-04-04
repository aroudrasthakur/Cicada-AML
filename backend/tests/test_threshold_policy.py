"""Tests for threshold policy and risk level assignment."""
import pytest
from unittest.mock import patch

from app.config import Settings


class TestDefaultThreshold:
    def test_fallback_risk_threshold_from_config(self):
        s = Settings(
            supabase_url="http://test",
            supabase_key="test",
            supabase_service_role_key="test",
        )
        assert s.fallback_risk_threshold == 0.75

    def test_custom_threshold(self):
        s = Settings(
            supabase_url="http://test",
            supabase_key="test",
            supabase_service_role_key="test",
            fallback_risk_threshold=0.6,
        )
        assert s.fallback_risk_threshold == 0.6


class TestPolicyApplication:
    def _apply_threshold(self, score, config):
        """Mirror the threshold logic from InferencePipeline."""
        decision = config.get("decision_threshold", 0.5)
        high = config.get("high_risk_threshold", 0.9)
        low_ceil = config.get("low_risk_ceiling", 0.3)

        if score >= high:
            return "high"
        elif score >= decision:
            return "medium"
        elif score <= low_ceil:
            return "low"
        else:
            return "medium-low"

    def test_high_risk(self):
        config = {"decision_threshold": 0.5, "high_risk_threshold": 0.9, "low_risk_ceiling": 0.3}
        assert self._apply_threshold(0.95, config) == "high"

    def test_medium_risk(self):
        config = {"decision_threshold": 0.5, "high_risk_threshold": 0.9, "low_risk_ceiling": 0.3}
        assert self._apply_threshold(0.6, config) == "medium"

    def test_medium_low_risk(self):
        config = {"decision_threshold": 0.5, "high_risk_threshold": 0.9, "low_risk_ceiling": 0.3}
        assert self._apply_threshold(0.4, config) == "medium-low"

    def test_low_risk(self):
        config = {"decision_threshold": 0.5, "high_risk_threshold": 0.9, "low_risk_ceiling": 0.3}
        assert self._apply_threshold(0.2, config) == "low"

    def test_boundary_decision_threshold(self):
        config = {"decision_threshold": 0.5, "high_risk_threshold": 0.9, "low_risk_ceiling": 0.3}
        assert self._apply_threshold(0.5, config) == "medium"

    def test_boundary_high_threshold(self):
        config = {"decision_threshold": 0.5, "high_risk_threshold": 0.9, "low_risk_ceiling": 0.3}
        assert self._apply_threshold(0.9, config) == "high"

    def test_boundary_low_ceiling(self):
        config = {"decision_threshold": 0.5, "high_risk_threshold": 0.9, "low_risk_ceiling": 0.3}
        assert self._apply_threshold(0.3, config) == "low"

    def test_custom_thresholds(self):
        config = {"decision_threshold": 0.7, "high_risk_threshold": 0.95, "low_risk_ceiling": 0.2}
        assert self._apply_threshold(0.5, config) == "medium-low"
        assert self._apply_threshold(0.8, config) == "medium"
        assert self._apply_threshold(0.96, config) == "high"
