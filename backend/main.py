from typing import Optional, List
import os
import re
import uuid
from datetime import datetime
import smtplib
from email.message import EmailMessage
import base64

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy import text
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "change-me-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

ALLOW_REGISTRATION = os.getenv("ALLOW_REGISTRATION", "false").lower() in {"1", "true", "yes"}

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'sentinel.db')}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

app = FastAPI(title="Sentinel AI")

_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://sentinel-ai-frontend.onrender.com",
    "https://sentinel-ai-1-0ppv.onrender.com",
]
_extra_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "").split(",")
    if o.strip()
]
_origin_regex = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"https://.*\.(zeabur\.app|onrender\.com|vercel\.app|railway\.app)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_origin_regex=_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Database Models
# -------------------------


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, index=True)
    company = Column(String, nullable=False)
    contact_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    title = Column(String, nullable=True)
    status = Column(String, default="new")  # new, researched, draft_created, approved, sent, replied
    created_at = Column(DateTime, default=datetime.utcnow)

    # Enriched lead / ICP fields
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    employee_count = Column(String, nullable=True)
    location = Column(String, nullable=True)
    source = Column(String, nullable=True)

    # Qualification
    icp_score = Column(String, nullable=True)  # store as simple string "82"
    qualification_reason = Column(Text, nullable=True)
    qualified = Column(String, nullable=True)  # "true"/"false"

    # Research layer (placeholders for future phases)
    research_summary = Column(Text, nullable=True)
    pain_points = Column(Text, nullable=True)
    personalization_note = Column(Text, nullable=True)
    cited_fact = Column(Text, nullable=True)


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(String, primary_key=True, index=True)
    lead_id = Column(String, nullable=False, index=True)
    company = Column(String, nullable=False)
    contact_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, approved, sent
    delivery_status = Column(String, default="queued")  # queued, sent, failed
    delivery_error = Column(Text, nullable=True)
    message_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # sales, support, ops, etc.
    description = Column(Text, nullable=True)
    status = Column(String, default="active")
    connected_tools = Column(Text, nullable=True)  # comma-separated for now
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)  # task, error, governance, roi
    task_name = Column(String, nullable=True)
    status = Column(String, nullable=True)
    revenue_impact = Column(String, nullable=True)  # store as string for now
    hours_saved = Column(String, nullable=True)  # string like "0.5"
    error_message = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Reasoning trace fields (Phase 4)
    lead_id = Column(String, nullable=True, index=True)
    tool_input = Column(Text, nullable=True)
    tool_output_preview = Column(Text, nullable=True)
    latency_ms = Column(String, nullable=True)
    tokens_in = Column(String, nullable=True)
    tokens_out = Column(String, nullable=True)
    cost_usd = Column(String, nullable=True)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, index=True)
    subject = Column(String, nullable=False)
    customer = Column(String, nullable=False)
    channel = Column(String, nullable=True)  # email, chat, etc.
    status = Column(String, default="open")  # open, drafted, resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class OpsTask(Base):
    __tablename__ = "ops_tasks"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="open")  # open, in_progress, done
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def _sqlite_ensure_column(table: str, column: str, ddl: str):
    """
    Minimal SQLite migration helper.
    Adds a column if it's missing (SQLite supports ALTER TABLE ADD COLUMN).
    """
    with engine.connect() as conn:
        cols = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        existing = {row[1] for row in cols}  # row[1] is column name
        if column not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
            conn.commit()


# Ensure new delivery-tracking columns exist even on old sentinel.db files.
_sqlite_ensure_column("drafts", "delivery_status", "delivery_status VARCHAR DEFAULT 'queued'")
_sqlite_ensure_column("drafts", "delivery_error", "delivery_error TEXT")
_sqlite_ensure_column("drafts", "message_id", "message_id VARCHAR")

# Backfill for older rows created before delivery_status existed.
with engine.connect() as conn:
    conn.execute(
        text(
            "UPDATE drafts SET delivery_status='sent' "
            "WHERE status='sent' AND (delivery_status IS NULL OR delivery_status='queued')"
        )
    )
    conn.commit()

# Ensure new Lead columns exist for ICP / research.
_sqlite_ensure_column("leads", "website", "website VARCHAR")
_sqlite_ensure_column("leads", "industry", "industry VARCHAR")
_sqlite_ensure_column("leads", "employee_count", "employee_count VARCHAR")
_sqlite_ensure_column("leads", "location", "location VARCHAR")
_sqlite_ensure_column("leads", "source", "source VARCHAR")
_sqlite_ensure_column("leads", "icp_score", "icp_score VARCHAR")
_sqlite_ensure_column("leads", "qualification_reason", "qualification_reason TEXT")
_sqlite_ensure_column("leads", "qualified", "qualified VARCHAR")
_sqlite_ensure_column("leads", "research_summary", "research_summary TEXT")
_sqlite_ensure_column("leads", "pain_points", "pain_points TEXT")
_sqlite_ensure_column("leads", "personalization_note", "personalization_note TEXT")
_sqlite_ensure_column("leads", "cited_fact", "cited_fact TEXT")

# AgentEvent reasoning-trace fields (Phase 4).
_sqlite_ensure_column("agent_events", "lead_id", "lead_id VARCHAR")
_sqlite_ensure_column("agent_events", "tool_input", "tool_input TEXT")
_sqlite_ensure_column("agent_events", "tool_output_preview", "tool_output_preview TEXT")
_sqlite_ensure_column("agent_events", "latency_ms", "latency_ms VARCHAR")
_sqlite_ensure_column("agent_events", "tokens_in", "tokens_in VARCHAR")
_sqlite_ensure_column("agent_events", "tokens_out", "tokens_out VARCHAR")
_sqlite_ensure_column("agent_events", "cost_usd", "cost_usd VARCHAR")

# Basic compatibility for new agent-related tables when an old DB exists.
_sqlite_ensure_column("tickets", "subject", "subject VARCHAR")
_sqlite_ensure_column("ops_tasks", "name", "name VARCHAR")

# -------------------------
# Dependency
# -------------------------


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# Schemas
# -------------------------


class LeadOut(BaseModel):
    id: str
    company: str
    contact_name: str
    email: str
    title: Optional[str] = None
    status: str
    created_at: datetime

    website: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None

    icp_score: Optional[str] = None
    qualification_reason: Optional[str] = None
    qualified: Optional[str] = None

    research_summary: Optional[str] = None
    pain_points: Optional[str] = None
    personalization_note: Optional[str] = None
    cited_fact: Optional[str] = None

    class Config:
        from_attributes = True


class DraftOut(BaseModel):
    id: str
    lead_id: str
    company: str
    contact_name: str
    email: str
    subject: str
    body: str
    status: str
    delivery_status: str
    delivery_error: Optional[str] = None
    message_id: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DraftUpdateIn(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None


class ActivityOut(BaseModel):
    id: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    total_leads: int
    new_leads: int
    drafts_pending: int
    drafts_approved: int
    drafts_sent: int


class LeadImportIn(BaseModel):
    company: str
    contact_name: str
    email: str
    title: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None


class ImportPayload(BaseModel):
    leads: List[LeadImportIn]


class AgentOut(BaseModel):
    id: str
    name: str
    role: str
    description: Optional[str] = None
    status: str
    connected_tools: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentStatsOut(BaseModel):
    agent_id: str
    name: str
    role: str
    tasks: int
    revenue_impact: float
    hours_saved: float
    errors: int


class GovernanceEventOut(BaseModel):
    id: str
    agent_id: str
    event_type: str
    task_name: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentEventOut(BaseModel):
    id: str
    agent_id: str
    event_type: str
    task_name: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    lead_id: Optional[str] = None
    tool_input: Optional[str] = None
    tool_output_preview: Optional[str] = None
    latency_ms: Optional[str] = None
    tokens_in: Optional[str] = None
    tokens_out: Optional[str] = None
    cost_usd: Optional[str] = None
    hours_saved: Optional[str] = None

    class Config:
        from_attributes = True


class RoiSummaryOut(BaseModel):
    total_hours_saved: float
    total_revenue_impact: float
    sales_emails_sent: int


class TicketOut(BaseModel):
    id: str
    subject: str
    customer: str
    channel: Optional[str] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OpsTaskOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
class UserCreate(BaseModel):
    email: str
    password: str
class UserOut(BaseModel):
    id: str
    email: str
    created_at: datetime
    class Config:
        from_attributes = True


# -------------------------
# Helpers
# -------------------------


def log_activity(db: Session, message: str):
    entry = ActivityLog(
        id=str(uuid.uuid4()),
        message=message,
    )
    db.add(entry)
    db.commit()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

def ensure_agent(
    db: Session,
    agent_id: str,
    name: str,
    role: str,
    connected_tools: Optional[str] = None,
) -> Agent:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        agent = Agent(
            id=agent_id,
            name=name,
            role=role,
            status="active",
            connected_tools=connected_tools,
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
    return agent


def log_agent_event(
    db: Session,
    *,
    agent_id: str,
    task_name: str,
    event_type: str = "task",
    status: Optional[str] = None,
    revenue_impact: Optional[float] = None,
    hours_saved: Optional[float] = None,
    error_message: Optional[str] = None,
    details: Optional[str] = None,
    lead_id: Optional[str] = None,
    tool_input: Optional[str] = None,
    tool_output_preview: Optional[str] = None,
    latency_ms: Optional[int] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    cost_usd: Optional[float] = None,
) -> "AgentEvent":
    event = AgentEvent(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        event_type=event_type,
        task_name=task_name,
        status=status,
        revenue_impact=str(revenue_impact) if revenue_impact is not None else None,
        hours_saved=str(hours_saved) if hours_saved is not None else None,
        error_message=error_message,
        details=details,
        lead_id=lead_id,
        tool_input=(tool_input[:500] if tool_input else None),
        tool_output_preview=(tool_output_preview[:500] if tool_output_preview else None),
        latency_ms=str(latency_ms) if latency_ms is not None else None,
        tokens_in=str(tokens_in) if tokens_in is not None else None,
        tokens_out=str(tokens_out) if tokens_out is not None else None,
        cost_usd=str(cost_usd) if cost_usd is not None else None,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def score_icp(lead: Lead) -> tuple[int, str, bool]:
    """
    Very simple ICP scoring heuristic.
    You can tune this later with real rules / models.
    """
    score = 50
    reasons: list[str] = []

    industry = (lead.industry or "").lower()
    if any(k in industry for k in ["software", "saas", "agency", "cpa", "logistics", "dental"]):
        score += 20
        reasons.append("Industry is a good fit.")

    title = (lead.title or "").lower()
    if any(t in title for t in ["owner", "founder", "partner", "director", "manager", "vp", "chief", "ceo"]):
        score += 15
        reasons.append("Senior decision-maker.")

    employees = (lead.employee_count or "").lower()
    if any(k in employees for k in ["1-10", "11-50", "small"]):
        score += 10
        reasons.append("Small team likely to feel manual ops pain.")

    location = (lead.location or "").lower()
    if location:
        reasons.append(f"Location: {lead.location}.")

    score = max(0, min(score, 100))
    qualified = score >= 70
    if qualified:
        reasons.append("High ICP fit.")
    else:
        reasons.append("Below target ICP threshold.")

    return score, " ".join(reasons), qualified


def send_email_smtp(*, to_email: str, subject: str, body: str) -> str:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM") or smtp_user
    smtp_tls = os.getenv("SMTP_TLS", "true").lower() in {"1", "true", "yes", "y"}

    missing = [
        name
        for name, val in [
            ("SMTP_HOST", smtp_host),
            ("SMTP_USER", smtp_user),
            ("SMTP_PASSWORD", smtp_password),
        ]
        if not val
    ]
    if missing:
        raise RuntimeError(
            "SMTP is not configured. Missing env var(s): " + ", ".join(missing)
        )
    if not smtp_from:
        raise RuntimeError("SMTP_FROM (or SMTP_USER) must be set")

    msg = EmailMessage()
    msg["To"] = to_email
    msg["From"] = smtp_from
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        if smtp_tls:
            server.starttls()
        server.login(smtp_user, smtp_password)
        response = server.send_message(msg)

    # SMTP doesn't reliably return a provider message id; return empty string.
    _ = response
    return ""


def send_email_gmail_api(*, to_email: str, subject: str, body: str) -> str:
    """
    Uses Gmail API (OAuth) to send a message.

    Required files/env:
    - GMAIL_CLIENT_SECRETS: path to Google OAuth client secrets json
    - GMAIL_TOKEN_FILE: optional path to token json (default: backend/gmail_token.json)
    """
    # Local import so SMTP-only users don't need google deps installed.
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    client_secrets = os.getenv("GMAIL_CLIENT_SECRETS")
    if not client_secrets:
        raise RuntimeError("GMAIL_CLIENT_SECRETS is not set")
    token_file = os.getenv("GMAIL_TOKEN_FILE") or os.path.join(BASE_DIR, "gmail_token.json")

    scopes = ["https://www.googleapis.com/auth/gmail.send"]
    creds: Optional[Credentials] = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes=scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets, scopes=scopes)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    msg = EmailMessage()
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service = build("gmail", "v1", credentials=creds)
    result = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()
    )
    return str(result.get("id") or "")


def send_email_resend(*, to_email: str, subject: str, body: str) -> str:
    """Send via Resend HTTPS API. Returns Resend message id.

    Renders the plain-text body as proper HTML (paragraph breaks, line
    breaks) so the email looks normal in Gmail / Outlook / etc. Also
    keeps the text version for client preview.
    """
    import html as html_lib
    import httpx

    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY not set")
    from_addr = os.getenv("RESEND_FROM", "Sentinel AI <onboarding@resend.dev>")
    reply_to = os.getenv("RESEND_REPLY_TO", "").strip() or None

    # Build an HTML version. Split on blank lines into paragraphs; convert
    # remaining single newlines into <br>.
    normalized = (body or "").replace("\r\n", "\n").strip()
    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    paragraph_html = "".join(
        f'<p style="margin:0 0 14px 0;">{html_lib.escape(p).replace(chr(10), "<br>")}</p>'
        for p in paragraphs
    )
    html_body = (
        '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,'
        'Helvetica,Arial,sans-serif;color:#111;line-height:1.55;'
        'font-size:15px;max-width:640px;">'
        f'{paragraph_html or html_lib.escape(normalized)}'
        '</div>'
    )

    payload: dict = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "text": normalized,
        "html": html_body,
    }
    if reply_to:
        payload["reply_to"] = reply_to

    with httpx.Client(timeout=20.0) as client:
        resp = client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"Resend {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
    return str(data.get("id") or "")


def send_email(*, to_email: str, subject: str, body: str) -> str:
    """Delivery priority:
    1. Resend (if RESEND_API_KEY) — recommended for hackathon
    2. Gmail API (if EMAIL_PROVIDER=gmail and Gmail OAuth configured)
    3. SMTP (if EMAIL_PROVIDER=smtp or as Gmail-API fallback)
    """
    if os.getenv("RESEND_API_KEY"):
        return send_email_resend(to_email=to_email, subject=subject, body=body)

    provider = (os.getenv("EMAIL_PROVIDER") or "gmail").lower()

    if provider == "gmail":
        try:
            return send_email_gmail_api(to_email=to_email, subject=subject, body=body)
        except Exception as gmail_err:
            smtp_host = os.getenv("SMTP_HOST")
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            if smtp_host and smtp_user and smtp_password:
                return send_email_smtp(to_email=to_email, subject=subject, body=body)
            raise gmail_err

    if provider == "smtp":
        return send_email_smtp(to_email=to_email, subject=subject, body=body)

    raise RuntimeError("Unsupported EMAIL_PROVIDER. Use 'gmail' or 'smtp'.")


# -------------------------
# Routes
# -------------------------


@app.get("/")
def root():
    return {"ok": True, "message": "Sentinel AI backend is running"}


@app.get("/leads", response_model=List[LeadOut])
def get_leads(db: Session = Depends(get_db)):
    return db.query(Lead).order_by(Lead.created_at.desc()).all()


@app.get("/agents", response_model=List[AgentOut])
def get_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).order_by(Agent.created_at.asc()).all()
    # Seed a few default agents if none exist yet.
    if not agents:
        ensure_agent(
            db,
            agent_id="sales-agent",
            name="Sales Agent",
            role="sales",
            connected_tools="Gmail,CSV,CRM",
        )
        ensure_agent(
            db,
            agent_id="support-agent",
            name="Customer Support Agent",
            role="support",
            connected_tools="Helpdesk,Knowledge Base,Slack",
        )
        ensure_agent(
            db,
            agent_id="ops-agent",
            name="Operations Agent",
            role="operations",
            connected_tools="Sheets,Notion,Slack",
        )
        agents = db.query(Agent).order_by(Agent.created_at.asc()).all()
    return agents


@app.get("/agent_stats", response_model=List[AgentStatsOut])
def get_agent_stats(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    events = db.query(AgentEvent).all()

    by_agent: dict[str, dict[str, object]] = {}
    for agent in agents:
        by_agent[agent.id] = {
            "agent_id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "tasks": 0,
            "revenue_impact": 0.0,
            "hours_saved": 0.0,
            "errors": 0,
        }

    for event in events:
        agg = by_agent.get(event.agent_id)
        if not agg:
            continue
        agg["tasks"] = int(agg["tasks"]) + 1  # type: ignore[index]
        if event.revenue_impact:
            try:
                agg["revenue_impact"] = float(agg["revenue_impact"]) + float(  # type: ignore[index]
                    event.revenue_impact
                )
            except ValueError:
                pass
        if event.hours_saved:
            try:
                agg["hours_saved"] = float(agg["hours_saved"]) + float(  # type: ignore[index]
                    event.hours_saved
                )
            except ValueError:
                pass
        if event.event_type in {"error", "governance"} or event.error_message:
            agg["errors"] = int(agg["errors"]) + 1  # type: ignore[index]

    return [
        AgentStatsOut(
            agent_id=a["agent_id"],  # type: ignore[index]
            name=a["name"],  # type: ignore[index]
            role=a["role"],  # type: ignore[index]
            tasks=int(a["tasks"]),  # type: ignore[index]
            revenue_impact=float(a["revenue_impact"]),  # type: ignore[index]
            hours_saved=float(a["hours_saved"]),  # type: ignore[index]
            errors=int(a["errors"]),  # type: ignore[index]
        )
        for a in by_agent.values()
    ]


@app.get("/governance_events", response_model=List[GovernanceEventOut])
def get_governance_events(db: Session = Depends(get_db)):
    """
    Governance & safety events: errors and explicit governance-type events.
    """
    events = (
        db.query(AgentEvent)
        .filter(
            (AgentEvent.event_type.in_(["error", "governance"]))
            | (AgentEvent.error_message.isnot(None))
        )
        .order_by(AgentEvent.created_at.desc())
        .limit(100)
        .all()
    )
    return events


@app.get("/agent_events", response_model=List[AgentEventOut])
def get_agent_events(
    lead_id: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """Full reasoning trace, optionally filtered to a single lead.
    Ordered ASC by created_at so the UI can render steps in order.
    """
    q = db.query(AgentEvent)
    if lead_id:
        q = q.filter(AgentEvent.lead_id == lead_id)
    events = (
        q.order_by(AgentEvent.created_at.asc())
        .limit(max(1, min(limit, 500)))
        .all()
    )
    return events


@app.get("/roi_summary", response_model=RoiSummaryOut)
def get_roi_summary(db: Session = Depends(get_db)):
    """
    High-level ROI view across all agents.
    """
    events = db.query(AgentEvent).all()
    total_hours = 0.0
    total_revenue = 0.0
    emails_sent = 0

    for e in events:
        if e.hours_saved:
            try:
                total_hours += float(e.hours_saved)
            except ValueError:
                pass
        if e.revenue_impact:
            try:
                total_revenue += float(e.revenue_impact)
            except ValueError:
                pass
        if e.agent_id == "sales-agent" and e.task_name == "send_email":
            emails_sent += 1

    return RoiSummaryOut(
        total_hours_saved=total_hours,
        total_revenue_impact=total_revenue,
        sales_emails_sent=emails_sent,
    )


@app.get("/drafts", response_model=List[DraftOut])
def get_drafts(db: Session = Depends(get_db)):
    return db.query(Draft).order_by(Draft.created_at.desc()).all()


@app.patch("/drafts/{draft_id}", response_model=DraftOut)
def update_draft(draft_id: str, payload: DraftUpdateIn, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending drafts can be edited")

    if payload.subject is not None:
        draft.subject = payload.subject
    if payload.body is not None:
        draft.body = payload.body

    db.commit()
    db.refresh(draft)
    log_activity(db, f"Edited draft for {draft.company}")
    return draft

@app.get("/leads", response_model=List[LeadOut])
def get_leads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Lead).order_by(Lead.created_at.desc()).all()

@app.get("/drafts", response_model=List[DraftOut])
def get_drafts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Draft).order_by(Draft.created_at.desc()).all()


@app.get("/activity", response_model=List[ActivityOut])
def get_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(100).all()


@app.get("/activity", response_model=List[ActivityOut])
def get_activity(db: Session = Depends(get_db)):
    return db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(100).all()


@app.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        total_leads = db.query(Lead).count()
        new_leads = db.query(Lead).filter(Lead.status == "new").count()
        drafts_pending = db.query(Draft).filter(Draft.status == "pending").count()
        drafts_approved = db.query(Draft).filter(Draft.status == "approved").count()
        drafts_sent = db.query(Draft).filter(Draft.status == "sent").count()
    except Exception:
        total_leads = 0
        new_leads = 0
        drafts_pending = 0
        drafts_approved = 0
        drafts_sent = 0

    return {
        "total_leads": total_leads,
        "new_leads": new_leads,
        "drafts_pending": drafts_pending,
        "drafts_approved": drafts_approved,
        "drafts_sent": drafts_sent,
    }


@app.post("/import_real_leads", response_model=List[LeadOut])
def import_real_leads(payload: ImportPayload, db: Session = Depends(get_db)):
    """
    Phase 1: real lead ingestion.
    This endpoint is the single entrypoint for:
    - lead provider APIs (your backend can call them and then POST here)
    - uploaded CSVs (frontend parses CSV and POSTs here)
    """
    created: list[Lead] = []

    for incoming in payload.leads:
        lead = Lead(
            id=str(uuid.uuid4()),
            company=incoming.company,
            contact_name=incoming.contact_name,
            email=incoming.email,
            title=incoming.title,
            status="new",
            website=incoming.website,
            industry=incoming.industry,
            employee_count=incoming.employee_count,
            location=incoming.location,
            source=incoming.source,
        )
        db.add(lead)
        created.append(lead)

    db.commit()

    log_activity(db, f"Imported {len(created)} real leads")
    return created


@app.post("/demo/seed", response_model=List[LeadOut])
def seed_demo(db: Session = Depends(get_db)):
    """Create the one perfect demo lead and one risky backup lead.

    The perfect lead is pending research — the live demo clicks Research on
    it to show the agent fetching a real website. The risky lead already has
    a pre-built draft containing 'ACT NOW!!! Guaranteed results' so the
    governance flag is guaranteed to fire on stage.
    """
    # Idempotent: clear any prior demo rows tagged with source='demo'.
    db.query(AgentEvent).filter(
        AgentEvent.lead_id.in_(
            [lead.id for lead in db.query(Lead).filter(Lead.source == "demo").all()]
        )
    ).delete(synchronize_session=False)
    db.query(Draft).filter(
        Draft.lead_id.in_(
            [lead.id for lead in db.query(Lead).filter(Lead.source == "demo").all()]
        )
    ).delete(synchronize_session=False)
    db.query(Lead).filter(Lead.source == "demo").delete(synchronize_session=False)
    db.commit()

    perfect = Lead(
        id=str(uuid.uuid4()),
        company="Lattice",
        contact_name="Jack Altman",
        email=os.getenv("DEMO_LEAD_EMAIL", "kvvaziran@gmail.com"),
        title="CEO & Co-founder",
        status="new",
        website="https://lattice.com",
        industry="HR software (B2B SaaS)",
        employee_count="201-500",
        location="San Francisco, CA",
        source="demo",
    )
    db.add(perfect)

    risky = Lead(
        id=str(uuid.uuid4()),
        company="Quick Wins Marketing",
        contact_name="Pat Stevens",
        email=os.getenv("DEMO_LEAD_EMAIL", "kvvaziran@gmail.com"),
        title="Sales Lead",
        status="draft_created",
        website="https://example.com",
        industry="marketing services",
        employee_count="11-50",
        location="Phoenix, AZ",
        source="demo",
        research_summary="Quick Wins Marketing is a small marketing agency.",
        pain_points="manual outreach; pressure to hit aggressive quotas",
        personalization_note="Reference the team's hustle for fast results.",
    )
    db.add(risky)
    db.commit()
    db.refresh(perfect)
    db.refresh(risky)

    # Pre-build a risky draft so the governance demo is one click away.
    risky_body = (
        "Hi Pat,\n\n"
        "ACT NOW!!! Guaranteed results. We deliver 100% lead growth with "
        "absolutely no risk. LIMITED TIME ONLY — DO NOT MISS OUT!!!\n\n"
        "Reply today and we'll have you crushing quota by next week.\n\n"
        "Best,\nKaran"
    )
    flags = check_draft_safety(risky_body)
    risky_draft = Draft(
        id=str(uuid.uuid4()),
        lead_id=risky.id,
        company=risky.company,
        contact_name=risky.contact_name,
        email=risky.email,
        subject="LIMITED TIME: 100% Guaranteed Lead Growth",
        body=risky_body,
        status="needs_review" if flags else "pending",
        delivery_status="queued",
    )
    db.add(risky_draft)
    db.commit()

    ensure_agent(
        db,
        agent_id="governance-agent",
        name="Governance Agent",
        role="governance",
        connected_tools="regex,policy",
    )
    log_agent_event(
        db,
        agent_id="governance-agent",
        task_name="governance_checked",
        event_type="governance",
        status="flagged" if flags else "passed",
        lead_id=risky.id,
        tool_input=f"len(body)={len(risky_body)}",
        tool_output_preview="; ".join(flags) if flags else "no risky patterns detected",
        error_message="; ".join(flags) if flags else None,
        hours_saved=0.1,
    )

    # Pin the perfect lead as the DEMO_MODE fail-safe target.
    os.environ["DEMO_LEAD_ID"] = perfect.id

    log_activity(db, f"Seeded demo: {perfect.company} (perfect) + {risky.company} (risky)")
    return [perfect, risky]


@app.post("/qualify_leads", response_model=List[LeadOut])
def qualify_leads(db: Session = Depends(get_db)):
    """
    Phase 2: ICP qualification layer.
    Scores all leads and marks qualified yes/no with a human-readable reason.
    """
    leads: list[Lead] = db.query(Lead).all()

    for lead in leads:
        score, reason, qualified = score_icp(lead)
        lead.icp_score = str(score)
        lead.qualification_reason = reason
        lead.qualified = "true" if qualified else "false"

    db.commit()

    log_activity(db, f"Qualified {len(leads)} leads with ICP scores")
    return db.query(Lead).order_by(Lead.created_at.desc()).all()


@app.post("/research_lead/{lead_id}", response_model=LeadOut)
def research_lead(lead_id: str, db: Session = Depends(get_db)):
    """Run the research agent: fetch the lead's website, ask the LLM for
    structured research with a cited_fact, log every step as an AgentEvent
    so the Reasoning Trace UI has data to show."""
    from agents.research_agent import run_research

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    ensure_agent(
        db,
        agent_id="research-agent",
        name="Research Agent",
        role="research",
        connected_tools="httpx,LLM,Bright Data (optional)",
    )

    result = run_research(lead)
    research = result["research"]
    trace = result["trace"]
    fallback = result.get("fallback", False)

    # Persist research onto the lead.
    lead.research_summary = research.get("company_summary") or lead.research_summary
    lead.pain_points = research.get("pain_points") or lead.pain_points
    lead.personalization_note = research.get("personalization_note") or lead.personalization_note
    lead.cited_fact = research.get("cited_fact")
    lead.status = "researched"
    db.commit()
    db.refresh(lead)

    # Log every step of the trace as an AgentEvent so the UI surfaces it.
    for step in trace:
        log_agent_event(
            db,
            agent_id="research-agent",
            task_name=step["task_name"],
            event_type="task",
            status=step.get("status") or "completed",
            lead_id=lead.id,
            tool_input=step.get("tool_input"),
            tool_output_preview=step.get("tool_output_preview"),
            latency_ms=step.get("latency_ms"),
            tokens_in=step.get("tokens_in"),
            tokens_out=step.get("tokens_out"),
            hours_saved=0.1,
            details=step.get("details"),
        )

    log_activity(
        db,
        f"Researched lead {lead.company}" + (" (fallback)" if fallback else ""),
    )
    return lead


@app.post("/generate_researched_draft/{lead_id}", response_model=DraftOut)
def generate_researched_draft(lead_id: str, db: Session = Depends(get_db)):
    """Generate a personalized outreach draft via a real LLM call.

    Uses the lead's research fields as context. DEMO_MODE fail-safe in
    call_llm guarantees a usable response even if the LLM provider fails.
    """
    from agents.llm import call_llm

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if not lead.research_summary or not lead.pain_points or not lead.personalization_note:
        raise HTTPException(
            status_code=400,
            detail="Lead has no research yet. Run /research_lead first.",
        )

    cited_fact = getattr(lead, "cited_fact", None)
    user_prompt = (
        f"Lead profile:\n"
        f"Company: {lead.company}\n"
        f"Contact: {lead.contact_name}\n"
        f"Industry: {lead.industry or 'unknown'}\n"
        f"Website: {lead.website or 'unknown'}\n\n"
        f"Research findings:\n"
        f"Summary: {lead.research_summary}\n"
        f"Pain points: {lead.pain_points}\n"
        f"Personalization note: {lead.personalization_note}\n"
        f"Cited fact: {cited_fact or '(none)'}\n\n"
        "Write the email body and a short subject line. "
        "Output exactly this JSON shape (no prose outside the JSON):\n"
        "{\"subject\": \"...\", \"body\": \"...\"}"
    )

    system_prompt = (
        "You write 120-word cold outreach emails for Sentinel, an AI agent "
        "platform that automates outbound sales for small businesses. "
        "Reference the company's pain points and, when present, the cited "
        "fact from their website — that proves you actually looked at them. "
        "Friendly and specific. No salesy language: never use 'guaranteed', "
        "'ACT NOW', 'limited time', '100%', or multiple exclamation marks. "
        "Sign off as 'Karan'."
    )

    llm = call_llm(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=600,
        response_format={"type": "json_object"},
    )

    subject, body = _parse_subject_body(
        llm["text"],
        fallback_subject=f"Quick idea for {lead.company}",
        fallback_body=llm["text"],
    )

    flags = check_draft_safety(subject + "\n" + body)
    draft_status = "needs_review" if flags else "pending"

    draft = Draft(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        company=lead.company,
        contact_name=lead.contact_name,
        email=lead.email,
        subject=subject,
        body=body,
        status=draft_status,
        delivery_status="queued",
    )
    db.add(draft)

    lead.status = "draft_created"
    db.commit()
    db.refresh(draft)

    ensure_agent(
        db,
        agent_id="sales-agent",
        name="Sales Agent",
        role="sales",
        connected_tools="Gmail,CSV,CRM,LLM",
    )
    log_agent_event(
        db,
        agent_id="sales-agent",
        task_name="draft_generated",
        event_type="task",
        status="completed" if not llm.get("fallback") else "fallback",
        hours_saved=0.5,
        lead_id=lead.id,
        tool_input=f"call_llm(model={os.getenv('OPENAI_MODEL', 'gpt-4o-mini')})",
        tool_output_preview=(body[:300] if body else "(empty)"),
        latency_ms=llm.get("latency_ms"),
        tokens_in=llm.get("tokens_in"),
        tokens_out=llm.get("tokens_out"),
    )

    ensure_agent(
        db,
        agent_id="governance-agent",
        name="Governance Agent",
        role="governance",
        connected_tools="regex,policy",
    )
    log_agent_event(
        db,
        agent_id="governance-agent",
        task_name="governance_checked",
        event_type="governance",
        status="flagged" if flags else "passed",
        lead_id=lead.id,
        tool_input=f"len(body)={len(body)}",
        tool_output_preview=(
            ("; ".join(flags)) if flags else "no risky patterns detected"
        ),
        error_message="; ".join(flags) if flags else None,
        hours_saved=0.1,
    )

    log_activity(
        db,
        f"Generated researched draft for {lead.company}"
        + (" (LLM fallback)" if llm.get("fallback") else "")
        + (" [governance: needs_review]" if flags else ""),
    )
    return draft


_RISKY_PATTERNS = [
    (re.compile(r"\bguarantee(?:d|s)?\b", re.IGNORECASE), "uses 'guarantee'"),
    (re.compile(r"\bact now\b", re.IGNORECASE), "uses 'ACT NOW'"),
    (re.compile(r"\blimited time\b", re.IGNORECASE), "uses 'limited time'"),
    (re.compile(r"!{3,}"), "uses excessive exclamation marks"),
    (re.compile(r"\b100\s*%\b"), "uses absolute claim '100%'"),
    (re.compile(r"\bno risk\b", re.IGNORECASE), "uses absolute claim 'no risk'"),
    (re.compile(r"\bzero downside\b", re.IGNORECASE), "uses absolute claim 'zero downside'"),
    (re.compile(r"\b(?:[A-Z]{3,}\b\s+){4,}[A-Z]{3,}\b"), "uses ALL-CAPS pressure language"),
]


def check_draft_safety(text: str) -> list[str]:
    """Regex-based governance check. Returns a list of human-readable flag
    reasons; an empty list means the draft is clean."""
    if not text:
        return []
    flags: list[str] = []
    for pattern, label in _RISKY_PATTERNS:
        if pattern.search(text):
            flags.append(label)
    return flags


def _parse_subject_body(text: str, *, fallback_subject: str, fallback_body: str) -> tuple[str, str]:
    """Best-effort parse of {subject, body} JSON. Tolerant of LLM quirks."""
    import json
    import re

    if not text:
        return fallback_subject, fallback_body
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        subject = (data.get("subject") or "").strip() or fallback_subject
        body = (data.get("body") or "").strip() or fallback_body
        return subject, body
    except Exception:
        return fallback_subject, fallback_body


# -------------------------
# Support Agent: tickets
# -------------------------


@app.post("/support/seed_tickets", response_model=List[TicketOut])
def seed_tickets(db: Session = Depends(get_db)):
    """
    Seed a few example support tickets for demo/monitoring.
    """
    examples = [
        ("Billing issue on latest invoice", "Maya @ Acme Logistics", "email"),
        ("Question about onboarding steps", "Leo @ NorthPeak Dental", "chat"),
        ("Feature request for reporting", "Priya @ BlueRiver CPA", "email"),
    ]

    created: list[Ticket] = []
    for subject, customer, channel in examples:
        ticket = Ticket(
            id=str(uuid.uuid4()),
            subject=subject,
            customer=customer,
            channel=channel,
            status="open",
        )
        db.add(ticket)
        created.append(ticket)

    ensure_agent(
        db,
        agent_id="support-agent",
        name="Customer Support Agent",
        role="support",
        connected_tools="Helpdesk,Knowledge Base,Slack",
    )
    db.commit()

    log_activity(db, f"Seeded {len(created)} support tickets")
    return db.query(Ticket).order_by(Ticket.created_at.desc()).all()


@app.get("/support/tickets", response_model=List[TicketOut])
def list_tickets(db: Session = Depends(get_db)):
    return db.query(Ticket).order_by(Ticket.created_at.desc()).all()


@app.post("/support/resolve_ticket/{ticket_id}", response_model=TicketOut)
def resolve_ticket(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status == "resolved":
        return ticket

    ticket.status = "resolved"
    ticket.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)

    ensure_agent(
        db,
        agent_id="support-agent",
        name="Customer Support Agent",
        role="support",
        connected_tools="Helpdesk,Knowledge Base,Slack",
    )
    log_agent_event(
        db,
        agent_id="support-agent",
        task_name="resolve_ticket",
        event_type="task",
        status="completed",
        hours_saved=0.15,
    )
    log_activity(db, f"Support agent resolved ticket: {ticket.subject}")
    return ticket


# -------------------------
# Ops Agent: internal tasks
# -------------------------


@app.post("/ops/seed_tasks", response_model=List[OpsTaskOut])
def seed_ops_tasks(db: Session = Depends(get_db)):
    examples = [
        ("Reconcile Stripe payouts", "Check yesterday's payouts against bank deposits."),
        ("Update weekly metrics sheet", "Copy latest numbers into the ops dashboard."),
        ("Clean up stale leads", "Close out leads older than 90 days with no activity."),
    ]

    created: list[OpsTask] = []
    for name, description in examples:
        task = OpsTask(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            status="open",
        )
        db.add(task)
        created.append(task)

    ensure_agent(
        db,
        agent_id="ops-agent",
        name="Operations Agent",
        role="operations",
        connected_tools="Sheets,Notion,Slack",
    )
    db.commit()

    log_activity(db, f"Seeded {len(created)} ops tasks")
    return db.query(OpsTask).order_by(OpsTask.created_at.desc()).all()


@app.get("/ops/tasks", response_model=List[OpsTaskOut])
def list_ops_tasks(db: Session = Depends(get_db)):
    return db.query(OpsTask).order_by(OpsTask.created_at.desc()).all()


@app.post("/ops/complete_task/{task_id}", response_model=OpsTaskOut)
def complete_ops_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(OpsTask).filter(OpsTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == "done":
        return task

    task.status = "done"
    task.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    ensure_agent(
        db,
        agent_id="ops-agent",
        name="Operations Agent",
        role="operations",
        connected_tools="Sheets,Notion,Slack",
    )
    log_agent_event(
        db,
        agent_id="ops-agent",
        task_name="complete_task",
        event_type="task",
        status="completed",
        hours_saved=0.3,
        revenue_impact=50.0,
    )
    log_activity(db, f"Ops agent completed task: {task.name}")
    return task


@app.post("/create_draft/{lead_id}", response_model=DraftOut)
def create_draft(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    draft = Draft(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        company=lead.company,
        contact_name=lead.contact_name,
        email=lead.email,
        subject=f"Idea for helping {lead.company}",
        body=(
            f"Hi {lead.contact_name},\n\n"
            f"I came across {lead.company} and wanted to reach out. "
            f"We help small businesses improve workflow efficiency and reduce manual overhead "
            f"with practical AI automation.\n\n"
            f"If helpful, I’d be happy to share a few ideas tailored to your team.\n\n"
            f"Best,\nKaran"
        ),
        status="pending",
        delivery_status="queued",
    )
    db.add(draft)

    lead.status = "draft_created"
    db.commit()
    db.refresh(draft)

    log_activity(db, f"Created draft for {lead.company}")
    # Attribute this work to the Sales Agent for monitoring/ROI.
    ensure_agent(
        db,
        agent_id="sales-agent",
        name="Sales Agent",
        role="sales",
        connected_tools="Gmail,CSV,CRM",
    )
    log_agent_event(
        db,
        agent_id="sales-agent",
        task_name="create_draft",
        event_type="task",
        status="completed",
        hours_saved=0.25,
    )
    return draft


@app.post("/approve_draft/{draft_id}", response_model=DraftOut)
def approve_draft(draft_id: str, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft.status = "approved"
    draft.approved_at = datetime.utcnow()

    lead = db.query(Lead).filter(Lead.id == draft.lead_id).first()
    if lead:
        lead.status = "approved"

    db.commit()
    db.refresh(draft)

    log_activity(db, f"Approved draft for {draft.company}")
    ensure_agent(
        db,
        agent_id="sales-agent",
        name="Sales Agent",
        role="sales",
        connected_tools="Gmail,CSV,CRM",
    )
    log_agent_event(
        db,
        agent_id="sales-agent",
        task_name="approve_draft",
        event_type="task",
        status="completed",
        hours_saved=0.1,
    )
    return draft

@app.post("/auth/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if not ALLOW_REGISTRATION:
        raise HTTPException(status_code=403, detail="Registration disabled")

    existing = get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        id=str(uuid.uuid4()),
        email=user_in.email,
        password_hash=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
def login(user_in: UserCreate, db: Session = Depends(get_db)):
    user = get_user_by_email(db, user_in.email)
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/send_draft/{draft_id}", response_model=DraftOut)
def send_draft(draft_id: str, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status != "approved":
        raise HTTPException(status_code=400, detail="Draft must be approved before sending")

    draft.delivery_status = "queued"
    draft.delivery_error = None
    db.commit()

    demo_mode = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"}
    email_configured = bool(
        os.getenv("RESEND_API_KEY")
        or os.getenv("SMTP_HOST")
        or os.getenv("GMAIL_CLIENT_SECRETS")
    )

    if demo_mode and not email_configured:
        # Stage-demo path: skip the real SMTP/Gmail call and mark sent. The
        # audience sees the same UI transition; no live email is required.
        message_id = f"demo-{uuid.uuid4().hex[:12]}"
        log_activity(db, f"[DEMO] Simulated send for {draft.email} (no SMTP configured)")
    else:
        try:
            message_id = send_email(
                to_email=draft.email,
                subject=draft.subject,
                body=draft.body,
            )
        except Exception as e:
            draft.delivery_status = "failed"
            draft.delivery_error = str(e)
            db.commit()
            log_activity(db, f"Failed sending draft to {draft.email}: {draft.delivery_error}")
            raise HTTPException(
                status_code=502,
                detail=f"Email delivery failed: {draft.delivery_error}",
            )

    draft.status = "sent"
    draft.delivery_status = "sent"
    draft.message_id = message_id or None
    draft.sent_at = datetime.utcnow()

    lead = db.query(Lead).filter(Lead.id == draft.lead_id).first()
    if lead:
        lead.status = "sent"

    db.commit()
    db.refresh(draft)

    log_activity(db, f"Sent draft to {draft.email}")
    ensure_agent(
        db,
        agent_id="sales-agent",
        name="Sales Agent",
        role="sales",
        connected_tools="Gmail,CSV,CRM",
    )
    log_agent_event(
        db,
        agent_id="sales-agent",
        task_name="send_email",
        event_type="task",
        status="completed",
        revenue_impact=0.0,
        hours_saved=0.25,
    )
    return draft



@app.on_event("startup")
def _bootstrap_demo() -> None:
    """Self-heal the demo if SQLite was wiped on container restart.

    Creates the canonical demo user and seeds Lattice + Quick Wins leads
    when missing. Idempotent. Disable with DEMO_AUTOBOOTSTRAP=false.
    """
    if os.getenv("DEMO_AUTOBOOTSTRAP", "true").lower() not in {"1", "true", "yes"}:
        return
    db = SessionLocal()
    try:
        if not get_user_by_email(db, "demo@sentinel.ai"):
            user = User(
                id=str(uuid.uuid4()),
                email="demo@sentinel.ai",
                password_hash=hash_password("sentinel2026"),
            )
            db.add(user)
            db.commit()
            print("[bootstrap] created demo user demo@sentinel.ai")
        if not db.query(Lead).filter(Lead.source == "demo").first():
            seed_demo(db)
            print("[bootstrap] seeded demo leads (Lattice + Quick Wins)")
    except Exception as exc:  # noqa: BLE001
        print(f"[bootstrap] failed: {exc}")
    finally:
        db.close()
