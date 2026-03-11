from sqlalchemy.orm import Session
from database.models import EmailDraft


def list_drafts(db: Session):
    return db.query(EmailDraft).all()


def get_draft_by_id(db: Session, draft_id: int):
    return db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()


def create_draft(db: Session, draft: EmailDraft):
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def save_changes(db: Session, obj):
    db.commit()
    db.refresh(obj)
    return obj
