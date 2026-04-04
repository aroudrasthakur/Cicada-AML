"""Determine data coverage tier and availability flags per record."""
from app.schemas.data_contract import CoverageTier, DataAvailabilityFlags, ApplicabilitySummary


def assess_data_availability(
    has_transactions: bool = True,
    has_address_tags: bool = False,
    has_entity_links: bool = False,
) -> DataAvailabilityFlags:
    """Determine coverage tier based on available data sources."""
    if has_entity_links:
        tier = CoverageTier.TIER2
    elif has_address_tags:
        tier = CoverageTier.TIER1
    else:
        tier = CoverageTier.TIER0
    
    return DataAvailabilityFlags(
        has_entity_intel=has_entity_links,
        has_address_tags=has_address_tags,
        coverage_tier=tier,
    )


def build_applicability_summary(
    applicability_vector: list[str],
) -> ApplicabilitySummary:
    """Summarize heuristic applicability from the 185-element vector."""
    applicable = sum(1 for a in applicability_vector if a == "applicable")
    missing = sum(1 for a in applicability_vector if a == "inapplicable_missing_data")
    out_of_scope = sum(1 for a in applicability_vector if a == "inapplicable_out_of_scope")
    
    return ApplicabilitySummary(
        total_rules=len(applicability_vector),
        applicable=applicable,
        inapplicable_missing_data=missing,
        inapplicable_out_of_scope=out_of_scope,
    )
