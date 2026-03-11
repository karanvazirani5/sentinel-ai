from sqlalchemy.orm import Session
from database.models import ActivityLog
from repositories.activity_repository import create_activity_log


def log_activity(db: Session, company_id, agent_id, event_type, message):
    log = ActivityLog(
        company_id=company_id,
        agent_id=agent_id,
        event_type=event_type,
        message=message,
    )
    return create_activity_log(db, log)
