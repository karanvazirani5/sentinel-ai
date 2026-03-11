from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Agent
from schemas.schemas import AgentCreate, AgentResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=list[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    return db.query(Agent).all()


@router.post("/", response_model=AgentResponse)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)):
    agent = Agent(
        id=payload.id,
        name=payload.name,
        category=payload.category,
        status=payload.status,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent
