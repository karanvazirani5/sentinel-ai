from pydantic import BaseModel
from typing import Optional


class LeadResearchRequest(BaseModel):
    industry: str
    source_agent_id: Optional[str] = None


class LeadResponse(BaseModel):
    id: int
    company_name: str
    contact_name: str
    email: str
    industry: str
    source_agent_id: Optional[str] = None

    class Config:
        orm_mode = True
