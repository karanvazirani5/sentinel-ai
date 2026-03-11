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


class CompanyCreate(BaseModel):
    id: str
    name: str
    industry: Optional[str] = None
    company_size: Optional[str] = None


class LeadCreate(BaseModel):
    company_name: str
    contact_name: str
    email: str
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


class LeadResearchRequest(BaseModel):
    industry: str
    source_agent_id: Optional[str] = None
class ActivityLogResponse(BaseModel):
    id: int
    company_id: Optional[str] = None
    agent_id: Optional[str] = None
    event_type: str
    message: str

    class Config:
        orm_mode = True
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


class CompanyCreate(BaseModel):
    id: str
    name: str
    industry: Optional[str] = None
    company_size: Optional[str] = None


class LeadCreate(BaseModel):
    company_name: str
    contact_name: str
    email: str
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


class LeadResearchRequest(BaseModel):
    industry: str
    source_agent_id: Optional[str] = None
class ActivityLogResponse(BaseModel):
    id: int
    company_id: Optional[str] = None
    agent_id: Optional[str] = None
    event_type: str
    message: str

    class Config:
        orm_mode = True

class EmailDraftResponse(BaseModel):
    id: int
    lead_id: int
    agent_id: Optional[str] = None
    subject: str
    body: str
    status: str

    class Config:
        orm_mode = True


class DraftCreateRequest(BaseModel):
    lead_id: int
    agent_id: Optional[str] = None
class DraftApprovalRequest(BaseModel):
    draft_id: int


class DraftSendRequest(BaseModel):
    draft_id: int
