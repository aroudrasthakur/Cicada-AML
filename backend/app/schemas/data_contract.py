from enum import Enum

from pydantic import BaseModel


class CoverageTier(str, Enum):
    TIER0 = "tier0"
    TIER1 = "tier1"
    TIER2 = "tier2"


class DataAvailabilityFlags(BaseModel):
    has_entity_intel: bool = False
    has_document_intel: bool = False
    has_address_tags: bool = False
    coverage_tier: CoverageTier = CoverageTier.TIER0


class ApplicabilitySummary(BaseModel):
    total_rules: int = 185
    applicable: int = 0
    inapplicable_missing_data: int = 0
    inapplicable_out_of_scope: int = 0
