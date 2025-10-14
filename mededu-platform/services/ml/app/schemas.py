from pydantic import BaseModel
from typing import List, Optional

class Session(BaseModel):
    startedAt: str
    endedAt: Optional[str] = None
    topic: Optional[str] = None
    focusLevel: Optional[int] = None

class ScheduleRequest(BaseModel):
    timezone: str
    targetDailyMinutes: int
    preferredWindows: list = []
    sessions: List[Session]

class PromptRequest(BaseModel):
    prompt: str
