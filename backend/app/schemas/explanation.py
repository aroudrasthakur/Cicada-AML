from typing import Optional

from pydantic import BaseModel


class ExplanationResponse(BaseModel):
    transaction_id: Optional[str] = None
    case_id: Optional[str] = None
    heuristics_fired: list[dict]
    lens_contributions: dict[str, float]
    pattern_type: Optional[str] = None
    laundering_stage: Optional[str] = None
    summary: str
    confidence: float
    coverage_tier: str
