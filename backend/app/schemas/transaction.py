from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TransactionCreate(BaseModel):
    transaction_id: str
    tx_hash: Optional[str] = None
    sender_wallet: str
    receiver_wallet: str
    amount: float
    asset_type: Optional[str] = None
    chain_id: Optional[str] = None
    timestamp: datetime
    fee: Optional[float] = None
    label: Optional[str] = None
    label_source: Optional[str] = None


class TransactionResponse(TransactionCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    limit: int
