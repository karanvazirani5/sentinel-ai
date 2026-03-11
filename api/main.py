from fastapi import FastAPI
from database.db import Base, engine
from database import models
from fastapi.middleware.cors import CORSMiddleware
from routes.health import router as health_router
from routes.agents import router as agents_router
from routes.leads import router as leads_router
from routes.activity import router as activity_router
from routes.outreach import router as outreach_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sentinel AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(agents_router)
app.include_router(leads_router)
app.include_router(activity_router)
app.include_router(outreach_router)


@app.get("/")
def root():
    return {"message": "Sentinel AI is running"}
