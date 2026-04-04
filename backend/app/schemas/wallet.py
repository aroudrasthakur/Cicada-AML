from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WalletCreate(BaseModel):
    wallet_address: str
    chain_id: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_in: float = 0
    total_out: float = 0


class WalletResponse(WalletCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}
