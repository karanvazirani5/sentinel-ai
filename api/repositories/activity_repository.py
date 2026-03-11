from sqlalchemy.orm import Session
from database.models import ActivityLog


def list_activity(db: Session):
    return db.query(ActivityLog).order_by(ActivityLog.id.desc()).all()


def create_activity_log(db: Session, log: ActivityLog):
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
