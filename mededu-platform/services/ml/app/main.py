from fastapi import FastAPI
from .schemas import ScheduleRequest, PromptRequest
from .inference import get_model
import json
from datetime import datetime

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/llm")
def llm(req: PromptRequest):
    text = get_model().generate(req.prompt)
    return {"text": text}

@app.post("/recommend/schedule")
def schedule(req: ScheduleRequest):
    stats = {
        "days": len({s.startedAt[:10] for s in req.sessions}),
        "total_sessions": len(req.sessions),
    }
    prompt = f"""You are a medical education study coach.
Timezone: {req.timezone}
Target daily minutes: {req.targetDailyMinutes}
Preferred windows: {json.dumps(req.preferredWindows)}
History summary: {json.dumps(stats)}

Propose a 7-day schedule with study blocks (start-end + topic: Anatomy/Physiology/Pharmacology/Pathology).
Return JSON with: days[{{date, blocks:[{{start,end,topic}}]}}], tips.
"""
    text = get_model().generate(prompt)
    return {"plan": text, "generatedAt": datetime.utcnow().isoformat() + "Z"}
