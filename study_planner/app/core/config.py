# app/core/config.py
from __future__ import annotations

import os
from typing import List, Optional
from pydantic import BaseModel


def _get_bool(env_name: str, default: bool = False) -> bool:
    val = os.getenv(env_name)
    if val is None:
        return default
    return str(val).strip().lower() not in {"0", "false", "no", "off", ""}


def _split_csv(env_name: str, default: str = "") -> List[str]:
    raw = os.getenv(env_name, default)
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


class Settings(BaseModel):
    # ------------------------- App -------------------------
    APP_NAME: str = os.getenv("APP_NAME", "MBBS Study Planner")
    DEBUG: bool = _get_bool("DEBUG", True)

    # ------------------------- DB -------------------------
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///app.db")

    # ------------------------- LLM (Groq) -------------------------
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # ------------------------- CORS -------------------------
    # e.g. CORS_ALLOW_ORIGINS="http://localhost:5173,http://127.0.0.1:3000"
    CORS_ALLOW_ORIGINS: List[str] = _split_csv("CORS_ALLOW_ORIGINS", "")

    # ------------------------- Derived flags -------------------------
    @property
    def HAS_GROQ(self) -> bool:
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())

    @property
    def DB_IS_SQLITE(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite:")

    @property
    def SQLALCHEMY_ECHO(self) -> bool:
        return self.DEBUG


settings = Settings()