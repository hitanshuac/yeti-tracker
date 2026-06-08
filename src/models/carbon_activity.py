from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class CarbonActivity(BaseModel):
    activity_id: UUID
    user_id: str
    activity_type: str
    carbon_kg: float = Field(..., ge=0)
    timestamp: datetime
