from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HeuristicRegistryEntry(BaseModel):
    id: int
    name: str
    environment: str
    lens_tags: list[str]
    description: str
    data_requirements: list[str]


class HeuristicResultResponse(BaseModel):
    transaction_id: str
    heuristic_vector: list[float]
    applicability_vector: list[str]
    triggered_ids: list[int]
    triggered_count: int
    top_typology: Optional[str] = None
    top_confidence: Optional[float] = None
    explanations: dict[str, str]
    scored_at: datetime


class HeuristicStatsResponse(BaseModel):
    most_triggered: list[dict]
    environment_distribution: dict[str, int]
    lens_distribution: dict[str, int]
    total_scored: int
