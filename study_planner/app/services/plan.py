from datetime import timedelta, date
from typing import List, Dict, Any
import os
import json
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.entities import PastItem, UpcomingEvent, StudyTask
from app.core.config import settings

# Optional Groq client
_client = None
try:
    if settings.GROQ_API_KEY:
        from groq import Groq
        _client = Groq(api_key=settings.GROQ_API_KEY)
except Exception:
    _client = None

_DEFAULT_MODEL = settings.GROQ_MODEL

SYSTEM_PROMPT = (
    "You are a medical education coach. Create concise, actionable study tasks for MBBS students. "
    "Use evidence-based strategies (spaced repetition, active recall, case-based learning). "
    "Keep each task specific and time-bounded. Output JSON ONLY following the schema."
)


def _llm_plan(messages: list[dict]) -> List[Dict[str, Any]]:
    """Calls Groq LLM to generate a study plan."""
    if not _client:
        return []

    try:
        resp = _client.chat.completions.create(
            model=_DEFAULT_MODEL,
            temperature=0.3,
            max_tokens=1200,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
    except Exception:
        return []

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "tasks" in parsed and isinstance(parsed["tasks"], list):
            return parsed["tasks"]
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    return []


def _fallback_plan(upc: UpcomingEvent, weak_topics: list[str]) -> List[Dict[str, Any]]:
    """Generate a simple deterministic plan if LLM is unavailable."""
    due = upc.date
    blocks = [
        {"title": f"Core reading: {upc.topic}", "days_before": 7, "hours": max(1, upc.hours // 5)},
        {"title": f"Active recall (flashcards): {upc.topic}", "days_before": 5, "hours": max(1, upc.hours // 6)},
        {"title": f"Clinical cases & images: {upc.topic}", "days_before": 3, "hours": max(1, upc.hours // 6)},
        {"title": "MCQ practice + review weak areas", "days_before": 2, "hours": max(1, upc.hours // 6)},
        {"title": "Final revision & rest", "days_before": 0, "hours": 1},
    ]

    if weak_topics:
        blocks.insert(1, {
            "title": f"Remediate weak topic(s): {', '.join(weak_topics[:2])}",
            "days_before": 6,
            "hours": 2,
        })

    tasks = []
    for b in blocks:
        tasks.append({
            "title": b["title"],
            "due_date": (due - timedelta(days=b["days_before"])).isoformat(),
            "hours": b["hours"],
        })
    return tasks


def generate_study_tasks(db: Session, student_id: int, model: str | None = None) -> list[StudyTask]:
    """Generate study tasks for all upcoming events of a student."""
    upcomings = db.scalars(
        select(UpcomingEvent).where(UpcomingEvent.student_id == student_id)
    ).all()
    created: list[StudyTask] = []

    # Identify weak topics (mark < 0.5)
    past = db.scalars(select(PastItem).where(PastItem.student_id == student_id)).all()
    weak_by_course: dict[str, list[str]] = {}
    for p in past:
        if p.mark < 0.5:
            weak_by_course.setdefault(p.course, []).append(p.topic)

    for upc in upcomings:
        weak_topics = weak_by_course.get(upc.course, [])

        user_prompt = {
            "role": "user",
            "content": (
                f"Student is preparing for upcoming topic '{upc.topic}' in the course '{upc.course}' on {upc.date}. "
                f"They have approximately {upc.hours} study hours. "
                f"Historically weak topics for this course: {weak_topics if weak_topics else 'None'}. "
                "Create 4-6 granular tasks with titles, due_date (YYYY-MM-DD between today and event date), and hours (1-3). "
                "Ensure tasks are MBBS-relevant (anatomy, physiology, pathology, etc.) and include images/cases practice when helpful. "
                "Schema: {{\"tasks\": [{{\"title\": str, \"due_date\": \"YYYY-MM-DD\", \"hours\": int}}]}}"
            ),
        }

        tasks_json = _llm_plan([
            {"role": "system", "content": SYSTEM_PROMPT},
            user_prompt,
        ])

        if not tasks_json:
            tasks_json = _fallback_plan(upc, weak_topics)

        for t in tasks_json:
            try:
                due = date.fromisoformat(str(t["due_date"]))
                hours = int(t.get("hours", 1))
                title = str(t["title"])[:200]
            except Exception:
                continue

            task = StudyTask(
                student_id=student_id,
                course=upc.course,
                event_idx=upc.idx,
                title=title,
                topic=upc.topic,
                due_date=due,
                hours=hours,
                status="not_started",
                completion_percent=0,
            )
            db.add(task)
            created.append(task)

    db.commit()
    return created
