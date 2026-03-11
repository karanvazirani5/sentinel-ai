from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from schemas.activity import ActivityLogResponse
from repositories.activity_repository import list_activity

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/", response_model=list[ActivityLogResponse])
def get_activity(db: Session = Depends(get_db)):
    return list_activity(db)
