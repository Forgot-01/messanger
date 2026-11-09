from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionDTO(BaseModel):
    id: UUID
    user_id: int
    ip_address: str
    user_agent: str

    last_activity: datetime
    last_ip_address: str
    revoked_at: datetime

    model_config = ConfigDict(from_attributes=True)
