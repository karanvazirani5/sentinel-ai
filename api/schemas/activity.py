from pydantic import BaseModel
from typing import Optional


class ActivityLogResponse(BaseModel):
    id: int
    company_id: Optional[str] = None
    agent_id: Optional[str] = None
    event_type: str
    message: str

    class Config:
        orm_mode = True
