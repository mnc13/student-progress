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

# ---------- FRONTEND (Static) ----------
# Serve the UI from app/frontend/
_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    # Mount under /frontend (won't interfere with /docs or API paths)
    app.mount("/frontend", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

    # Redirect root to the SPA
    @app.get("/")
    def root_redirect():
        return RedirectResponse(url="/frontend/")
else:
    # If no frontend folder, keep a simple root so "/" isn't 404
    @app.get("/")
    def root_ok():
        return {"ok": True}
