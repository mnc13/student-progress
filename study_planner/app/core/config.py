import os
from pydantic import BaseModel

class Settings(BaseModel):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///app.db")
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    APP_NAME: str = "MBBS Study Planner"

settings = Settings()
