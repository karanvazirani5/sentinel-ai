from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from schemas.outreach import (
    DraftCreateRequest,
    EmailDraftResponse,
    DraftApprovalRequest,
    DraftSendRequest,
)
from services.outreach_service import (
    list_drafts,
    create_outreach_draft,
    approve_draft,
    send_draft,
)

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.get("/drafts", response_model=list[EmailDraftResponse])
def get_drafts(db: Session = Depends(get_db)):
    return list_drafts(db)


@router.post("/draft", response_model=EmailDraftResponse)
def create_draft(payload: DraftCreateRequest, db: Session = Depends(get_db)):
    return create_outreach_draft(
        db=db,
        lead_id=payload.lead_id,
        agent_id=payload.agent_id,
    )


@router.post("/approve", response_model=EmailDraftResponse)
def approve(payload: DraftApprovalRequest, db: Session = Depends(get_db)):
    return approve_draft(db=db, draft_id=payload.draft_id)


@router.post("/send", response_model=EmailDraftResponse)
def send(payload: DraftSendRequest, db: Session = Depends(get_db)):
    return send_draft(db=db, draft_id=payload.draft_id)
