from pydantic import BaseModel
from typing import Optional


class DraftCreateRequest(BaseModel):
    lead_id: int
    agent_id: Optional[str] = None


class DraftApprovalRequest(BaseModel):
    draft_id: int


class DraftSendRequest(BaseModel):
    draft_id: int


class EmailDraftResponse(BaseModel):
    id: int
    lead_id: int
    agent_id: Optional[str] = None
    subject: str
    body: str
    status: str

    class Config:
        orm_mode = True
