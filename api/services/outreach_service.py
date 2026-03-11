from sqlalchemy.orm import Session
from fastapi import HTTPException

from database.models import EmailDraft
from repositories.lead_repository import get_lead_by_id
from repositories.outreach_repository import (
    list_drafts as repo_list_drafts,
    create_draft,
    get_draft_by_id,
    save_changes,
)
from services.activity_service import log_activity
from services.ai_service import generate_outreach_email


def list_drafts(db: Session):
    return repo_list_drafts(db)


def create_outreach_draft(db: Session, lead_id: int, agent_id: str = None):
    lead = get_lead_by_id(db, lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    subject = f"Quick idea for {lead.company_name}"
    body = generate_outreach_email(
        lead.company_name,
        lead.contact_name,
        lead.industry,
    )

    draft = EmailDraft(
        lead_id=lead.id,
        agent_id=agent_id,
        subject=subject,
        body=body,
        status="draft",
    )

    saved_draft = create_draft(db, draft)

    log_activity(
        db=db,
        company_id=None,
        agent_id=agent_id,
        event_type="outreach_draft_created",
        message=f"Created AI outreach draft for lead_id={lead.id} ({lead.company_name})",
    )

    return saved_draft


def approve_draft(db: Session, draft_id: int):
    draft = get_draft_by_id(db, draft_id)

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft.status = "approved"
    draft = save_changes(db, draft)

    log_activity(
        db=db,
        company_id=None,
        agent_id=draft.agent_id,
        event_type="outreach_draft_approved",
        message=f"Approved draft_id={draft.id}",
    )

    return draft


def send_draft(db: Session, draft_id: int):
    draft = get_draft_by_id(db, draft_id)

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status != "approved":
        raise HTTPException(status_code=400, detail="Draft must be approved before sending")

    draft.status = "sent"
    draft = save_changes(db, draft)

    log_activity(
        db=db,
        company_id=None,
        agent_id=draft.agent_id,
        event_type="outreach_draft_sent",
        message=f"Marked draft_id={draft.id} as sent",
    )

    return draft
