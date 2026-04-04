from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NetworkCaseResponse(BaseModel):
    id: str
    case_name: str
    typology: Optional[str] = None
    risk_score: Optional[float] = None
    total_amount: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    explanation: Optional[str] = None
    graph_snapshot_path: Optional[str] = None
    wallets: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}
