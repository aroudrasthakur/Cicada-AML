"""Tests for data contract schemas and availability service."""
import pytest

from app.schemas.data_contract import CoverageTier, DataAvailabilityFlags, ApplicabilitySummary
from app.services.data_availability_service import assess_data_availability, build_applicability_summary


class TestCoverageTiers:
    def test_tier0_with_only_transactions(self):
        flags = assess_data_availability(has_transactions=True)
        assert flags.coverage_tier == CoverageTier.TIER0

    def test_tier1_with_address_tags(self):
        flags = assess_data_availability(has_transactions=True, has_address_tags=True)
        assert flags.coverage_tier == CoverageTier.TIER1

    def test_tier2_with_entity_links(self):
        flags = assess_data_availability(has_transactions=True, has_entity_links=True)
        assert flags.coverage_tier == CoverageTier.TIER2

    def test_tier2_with_document_events(self):
        flags = assess_data_availability(has_transactions=True, has_document_events=True)
        assert flags.coverage_tier == CoverageTier.TIER2

    def test_tier2_takes_precedence_over_tier1(self):
        flags = assess_data_availability(
            has_transactions=True,
            has_address_tags=True,
            has_entity_links=True,
        )
        assert flags.coverage_tier == CoverageTier.TIER2


class TestDataAvailabilityFlags:
    def test_default_flags_are_false(self):
        flags = assess_data_availability(has_transactions=True)
        assert flags.has_entity_intel is False
        assert flags.has_document_intel is False
        assert flags.has_address_tags is False

    def test_entity_flag_set(self):
        flags = assess_data_availability(has_entity_links=True)
        assert flags.has_entity_intel is True

    def test_document_flag_set(self):
        flags = assess_data_availability(has_document_events=True)
        assert flags.has_document_intel is True

    def test_address_tags_flag_set(self):
        flags = assess_data_availability(has_address_tags=True)
        assert flags.has_address_tags is True


class TestApplicabilitySummary:
    def test_summary_counts(self):
        vec = ["applicable"] * 100 + ["inapplicable_missing_data"] * 60 + ["inapplicable_out_of_scope"] * 25
        summary = build_applicability_summary(vec)
        assert summary.total_rules == 185
        assert summary.applicable == 100
        assert summary.inapplicable_missing_data == 60
        assert summary.inapplicable_out_of_scope == 25

    def test_empty_vector(self):
        summary = build_applicability_summary([])
        assert summary.total_rules == 0
        assert summary.applicable == 0

    def test_all_applicable(self):
        vec = ["applicable"] * 185
        summary = build_applicability_summary(vec)
        assert summary.applicable == 185
        assert summary.inapplicable_missing_data == 0
        assert summary.inapplicable_out_of_scope == 0
