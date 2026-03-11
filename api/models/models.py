from sqlalchemy import Column, String, ForeignKey, Integer, Text
from database.db import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    status = Column(String, nullable=False)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    event_type = Column(String, nullable=False)
    message = Column(String, nullable=False)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    contact_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    source_agent_id = Column(String, ForeignKey("agents.id"), nullable=True)


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="draft")
