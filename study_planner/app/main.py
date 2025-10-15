# app/main.py
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

app = FastAPI(title=settings.APP_NAME)

# CORS for local dev (frontend may be on a different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- DB BOOTSTRAP ----------
def _init_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        try:
            cnt = db.execute(text("SELECT COUNT(*) FROM students")).scalar_one()
        except Exception:
            cnt = 0

        if cnt == 0:
            # Try either CSV name; bootstrap from the first one that exists
            data_dir = Path(__file__).resolve().parent.parent / "data"
            candidates = [
                data_dir / "mbbs_personalization.csv",
            ]
            for csv_path in candidates:
                if csv_path.exists():
                    bootstrap_from_csv(db, csv_path)
                    break

_init_db()

# ---------- API ROUTERS ----------
app.include_router(auth.router)
app.include_router(students.router)

# ---------- HEALTH ----------
@app.get("/healthz")
def health():
    return {"ok": True, "app": settings.APP_NAME}


