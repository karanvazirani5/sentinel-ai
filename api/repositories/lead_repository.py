from sqlalchemy.orm import Session
from database.models import Lead


def list_leads(db: Session):
    return db.query(Lead).all()


def create_leads(db: Session, leads):
    for lead in leads:
        db.add(lead)
    db.commit()
    return leads


def get_lead_by_id(db: Session, lead_id: int):
    return db.query(Lead).filter(Lead.id == lead_id).first()
