from pydantic import BaseModel
from typing import Optional


class AgentCreate(BaseModel):
    id: str
    name: str
    category: str
    status: str
    company_id: Optional[str] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    category: str
    status: str
    company_id: Optional[str] = None

    class Config:
        orm_mode = True
