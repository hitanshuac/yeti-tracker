from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class RawTransaction(BaseModel):
    transaction_id: UUID
    user_id: str
    mcc: str
    amount_inr: float = Field(..., ge=0)
    timestamp: datetime
