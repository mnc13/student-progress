# app/main.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from pathlib import Path

from app.core.config import settings
from app.models.db import engine, SessionLocal, Base
from app.models import entities  # Ensure models are registered
from app.utils.csv_loader import bootstrap_from_csv
from app.routers import auth, students
from app.routers.content import router as content_router

app = FastAPI(title=settings.APP_NAME)

# --------------------------- CORS ---------------------------
# CORS for local dev (frontend may be on a different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------- DB init & migrations ---------------------------

def _migrate_upcoming_events_is_final() -> None:
    """Best-effort migration: add UpcomingEvent.is_final if missing."""
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql(
                "ALTER TABLE upcoming_events ADD COLUMN is_final BOOLEAN DEFAULT 0"
            )
            conn.commit()
    except Exception:
        # already present / fresh DB — ignore
        pass


def _init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_upcoming_events_is_final()
    with SessionLocal() as db:
        try:
            cnt = db.execute(text("SELECT COUNT(*) FROM students")).scalar_one()
        except Exception:
            cnt = 0
        if cnt == 0:
            csv_path = Path(__file__).resolve().parent.parent / "data" / "mbbs_personalization.csv"
            bootstrap_from_csv(db, csv_path)


_init_db()

# --------------------------- Routers ---------------------------
app.include_router(auth.router)
app.include_router(students.router)
app.include_router(content_router)

# Optional: mount a /static directory if you have one
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# --------------------------- Root & Health ---------------------------
@app.get("/")
def root():
    # Quick redirect to interactive docs
    return RedirectResponse(url="/docs")


@app.get("/healthz")
def health():
    return {"ok": True, "app": settings.APP_NAME}


@app.get("/debug/llm")
def debug_llm():
    return {
        "has_key": bool(getattr(settings, "HAS_GROQ", False)),
        "model": getattr(settings, "GROQ_MODEL", None),
        "client_ready": bool(getattr(settings, "HAS_GROQ", False)),
    }
