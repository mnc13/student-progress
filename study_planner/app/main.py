from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path

from app.core.config import settings
from app.models.db import engine, SessionLocal, Base
from app.models import entities  # ✅ Import your models here to register them
from app.utils.csv_loader import bootstrap_from_csv
from app.routers import auth, students

app = FastAPI(title=settings.APP_NAME)

# CORS for local dev (frontend may be on a different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Create tables and bootstrap data once
def _init_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        # If no students yet, bootstrap from CSV
        cnt = db.execute(text("SELECT COUNT(*) FROM students")).scalar_one()
        if cnt == 0:
            csv_path = Path(__file__).resolve().parent.parent / "data" / "mbbs_personalization.csv"
            bootstrap_from_csv(db, csv_path)

_init_db()

# Routers
app.include_router(auth.router)
app.include_router(students.router)


@app.get("/healthz")
def health():
    return {"ok": True, "app": settings.APP_NAME}



@app.get("/")
def root():
    return {"status": "ok", "app": settings.APP_NAME, "docs": "/docs"}

