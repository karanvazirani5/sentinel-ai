from sqlalchemy.orm import Session
from database.models import Lead
from repositories.lead_repository import list_leads as repo_list_leads, create_leads
from services.activity_service import log_activity


def list_leads(db: Session):
    return repo_list_leads(db)


def generate_sample_leads(db: Session, industry: str, source_agent_id: str = None):
    leads = [
        Lead(
            company_name=f"{industry} Growth Co",
            contact_name="Sarah Johnson",
            email="sarah@growthco.com",
            industry=industry,
            source_agent_id=source_agent_id,
        ),
        Lead(
            company_name=f"{industry} Labs",
            contact_name="Mike Chen",
            email="mike@labs.com",
            industry=industry,
            source_agent_id=source_agent_id,
        ),
        Lead(
            company_name=f"{industry} Partners",
            contact_name="Emily Davis",
            email="emily@partners.com",
            industry=industry,
            source_agent_id=source_agent_id,
        ),
    ]

    create_leads(db, leads)

    log_activity(
        db=db,
        company_id=None,
        agent_id=source_agent_id,
        event_type="lead_research",
        message=f"Generated 3 leads for industry: {industry}",
    )

    return repo_list_leads(db)
