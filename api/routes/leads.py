from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from schemas.lead import LeadResponse, LeadResearchRequest
from services.lead_service import list_leads, generate_sample_leads

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/", response_model=list[LeadResponse])
def get_leads(db: Session = Depends(get_db)):
    return list_leads(db)


@router.post("/research", response_model=list[LeadResponse])
def research_leads(payload: LeadResearchRequest, db: Session = Depends(get_db)):
    return generate_sample_leads(
        db=db,
        industry=payload.industry,
        source_agent_id=payload.source_agent_id,
    )
