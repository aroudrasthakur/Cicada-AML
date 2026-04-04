from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: str
    case_id: str
    title: str
    report_path: Optional[str] = None
    generated_at: datetime

    model_config = {"from_attributes": True}
