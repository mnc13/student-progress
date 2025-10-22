# app/routers/students.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case, delete

from app.core.config import settings
from app.models.db import SessionLocal
from app.models.entities import Student, PastItem, UpcomingEvent, StudyTask
from app.models.schemas import (
    CourseOut,
    PastItemOut,
    UpcomingEventOut,
    StudyTaskOut,
    GeneratePlanResponse,
    ProgressSummary,
)
from app.services.plan import generate_study_tasks, fetch_topic_enrichment, fetch_subtopic_map_with_pubmed

router = APIRouter(prefix="/students", tags=["students"]) 

# ---------------------------------------------------------------------------
# DB session dependency
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_student(db: Session, student_id: int) -> None:
    if not db.scalar(select(Student).where(Student.student_id == student_id)):
        raise HTTPException(status_code=404, detail="student_id not found")


# ---------------------------------------------------------------------------
# Courses & Past Items
# ---------------------------------------------------------------------------

@router.get("/{student_id}/courses", response_model=List[CourseOut])
def list_courses(student_id: int, db: Session = Depends(get_db)):
    _ensure_student(db, student_id)
    rows = db.execute(
        select(PastItem.course).where(PastItem.student_id == student_id).distinct()
    ).all()
    return [{"course": r[0]} for r in rows]


@router.get("/{student_id}/courses/{course}/past", response_model=List[PastItemOut])
def past_items(student_id: int, course: str, db: Session = Depends(get_db)):
    _ensure_student(db, student_id)
    items = db.scalars(
        select(PastItem)
        .where(PastItem.student_id == student_id, PastItem.course == course)
        .order_by(PastItem.idx)
    ).all()
    return [
        {
            "idx": it.idx,
            "topic": it.topic,
            "hours": it.hours,
            "mark": it.mark,
            "percent": int(round((it.mark or 0) * 100)),
        }
        for it in items
    ]


# ---------------------------------------------------------------------------
# Upcoming events
# ---------------------------------------------------------------------------

@router.get("/{student_id}/upcoming", response_model=List[UpcomingEventOut])
def upcoming(
    student_id: int,
    course: str | None = Query(None),
    include_past: bool = Query(False, description="Include past-dated upcoming rows"),
    db: Session = Depends(get_db),
):
    _ensure_student(db, student_id)
    stmt = select(UpcomingEvent).where(UpcomingEvent.student_id == student_id)
    if not include_past:
        from datetime import date
        today = date.today()
        stmt = stmt.where(UpcomingEvent.date >= today)
    if course:
        stmt = stmt.where(UpcomingEvent.course == course)
    events = db.scalars(stmt.order_by(UpcomingEvent.date)).all()
    return [
        {
            "id": ev.id,
            "idx": ev.idx,
            "course": ev.course,
            "topic": ev.topic,
            "hours": ev.hours,
            "date": ev.date,
            "is_final": bool(getattr(ev, "is_final", False)),
        }
        for ev in events
    ]


# ---------------------------------------------------------------------------
# Study Plan generation
# ---------------------------------------------------------------------------

@router.post("/{student_id}/study-plan/generate", response_model=GeneratePlanResponse)
def generate_plan(
    student_id: int,
    course: str = Query(...),
    final_only: bool = Query(False, description="If true, only generate for finals (by event flag)"),
    use_llm: bool = Query(True, description="Force LLM usage; 503 if missing"),
    db: Session = Depends(get_db),
):
    _ensure_student(db, student_id)

    # Clear tasks in the requested scope to avoid duplicates
    if final_only:
        # Delete tasks only for events flagged as finals (requires UpcomingEvent.is_final in your model)
        finals = db.scalars(
            select(UpcomingEvent.idx).where(
                UpcomingEvent.student_id == student_id,
                UpcomingEvent.course == course,
                # Uncomment if you have the column in your ORM model:
                # UpcomingEvent.is_final == True,
            )
        ).all()
        db.execute(
            delete(StudyTask).where(
                StudyTask.student_id == student_id,
                StudyTask.course == course,
                StudyTask.event_idx.in_(finals or [-1]),
            )
        )
    else:
        db.execute(
            delete(StudyTask).where(
                StudyTask.student_id == student_id, StudyTask.course == course
            )
        )
    db.commit()

    try:
        created_rows = generate_study_tasks(
            db, student_id, course=course, final_only=final_only, use_llm=use_llm
        )
    except RuntimeError as e:
        # Surfaces as 503 when LLM was explicitly required but not configured
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "created_tasks": [
            {
                "id": t.id,
                "event_idx": t.event_idx,
                "course": t.course,
                "title": t.title,
                "topic": t.topic,
                "due_date": t.due_date,
                "hours": t.hours,
                "status": t.status,
                "completion_percent": t.completion_percent,
            }
            for t in created_rows
        ]
    }


# ---------------------------------------------------------------------------
# Tasks CRUD
# ---------------------------------------------------------------------------

@router.get("/{student_id}/tasks", response_model=List[StudyTaskOut])
def list_tasks(
    student_id: int, course: str | None = Query(None), db: Session = Depends(get_db)
):
    _ensure_student(db, student_id)
    stmt = select(StudyTask).where(StudyTask.student_id == student_id)
    if course:
        stmt = stmt.where(StudyTask.course == course)
    tasks = db.scalars(stmt.order_by(StudyTask.due_date)).all()
    return [
        {
            "id": t.id,
            "event_idx": t.event_idx,
            "course": t.course,
            "title": t.title,
            "topic": t.topic,
            "due_date": t.due_date,
            "hours": t.hours,
            "status": t.status,
            "completion_percent": t.completion_percent,
            "context": getattr(t, "context", None),
        }
        for t in tasks
    ]


@router.patch("/{student_id}/tasks/{task_id}", response_model=StudyTaskOut)
def update_task(
    student_id: int,
    task_id: int,
    status: str | None = None,
    completion_percent: int | None = None,
    db: Session = Depends(get_db),
):
    _ensure_student(db, student_id)
    t = db.get(StudyTask, task_id)
    if not t or t.student_id != student_id:
        raise HTTPException(status_code=404, detail="task not found")

    changed = False
    if status is not None:
        if status not in {"not_started", "in_progress", "done"}:
            raise HTTPException(status_code=400, detail="invalid status")
        t.status = status
        if status == "done":
            t.completion_percent = 100
        elif status == "not_started":
            t.completion_percent = 0
        changed = True

    if completion_percent is not None:
        if not (0 <= completion_percent <= 100):
            raise HTTPException(status_code=400, detail="invalid completion_percent")
        t.completion_percent = completion_percent
        if completion_percent == 100:
            t.status = "done"
        elif completion_percent == 0:
            t.status = "not_started"
        else:
            t.status = "in_progress"
        changed = True

    if changed:
        db.add(t)
        db.commit()
        db.refresh(t)

    return {
        "id": t.id,
        "event_idx": t.event_idx,
        "course": t.course,
        "title": t.title,
        "topic": t.topic,
        "due_date": t.due_date,
        "hours": t.hours,
        "status": t.status,
        "completion_percent": t.completion_percent,
        "context": getattr(t, "context", None),
    }


# ---------------------------------------------------------------------------
# Progress rollups
# ---------------------------------------------------------------------------

@router.get("/{student_id}/progress", response_model=List[ProgressSummary])
def progress(student_id: int, course: str | None = Query(None), db: Session = Depends(get_db)):
    _ensure_student(db, student_id)
    stmt = select(
        StudyTask.event_idx,
        StudyTask.course,
        StudyTask.topic,
        StudyTask.due_date,
        func.coalesce(func.avg(StudyTask.completion_percent), 0).label("avg_pct"),
        func.count(StudyTask.id).label("cnt"),
        func.sum(case((StudyTask.status == "done", 1), else_=0)).label("done_cnt"),
    ).where(StudyTask.student_id == student_id)
    if course:
        stmt = stmt.where(StudyTask.course == course)
    stmt = stmt.group_by(StudyTask.event_idx, StudyTask.course, StudyTask.topic, StudyTask.due_date)
    rows = db.execute(stmt).all()
    return [
        {
            "event_idx": r[0],
            "course": r[1],
            "topic": r[2],
            "due_date": r[3],
            "completion_percent": int(round((r[4] or 0))),
            "completed_tasks": int(r[6] or 0),
            "total_tasks": int(r[5] or 0),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Topic enrichment (subtopics + curated links via LLM) and helpers
# ---------------------------------------------------------------------------

@router.post("/{student_id}/topic-enrichment")
def topic_enrichment(
    student_id: int,
    course: str = Query(...),
    topics: List[str] = Body(..., embed=True, description="List of topic strings"),
    db: Session = Depends(get_db),
):
    _ensure_student(db, student_id)
    return fetch_topic_enrichment(course, topics)


@router.get("/debug/groq")
def debug_groq():
    # Do NOT print the key; only reveal the presence of *a* key and the configured model
    return {"has_key": bool(settings.GROQ_API_KEY), "model": getattr(settings, "GROQ_MODEL", None)}


@router.get("/courses/{course}/topics/{topic}/syllabus")
def syllabus_proxy(course: str, topic: str):
    # Lightweight passthrough for a single-topic enrichment view
    data_enrich = fetch_topic_enrichment(course, [topic])
    data_map = fetch_subtopic_map_with_pubmed(topic, course)
    subtopics = []
    if data_map:
        for sec in data_map.get("subtopics", []):
            subtopics.extend(sec.get("items", []))
    else:
        subtopics = data_enrich.get(topic, {}).get("subtopics", [])
    resources = data_enrich.get(topic, {}).get("resources", [])
    pubmed = data_map.get("pubmed", {}) if data_map else data_enrich.get(topic, {}).get("pubmed", {})
    return {"subtopics": subtopics, "resources": resources, "pubmed": pubmed}


# ---------------------------------------------------------------------------
# Subtopic Map (with PubMed bundle)
# ---------------------------------------------------------------------------

@router.post("/{student_id}/subtopic-map")
def subtopic_map(
    student_id: int,
    course: str = Query(..., description="Course name, e.g., Anatomy"),
    topic: str = Body(..., embed=True, description="Single topic string"),
    db: Session = Depends(get_db),
):
    """Return a structured subtopic map + study path for a single topic, with PubMed links."""
    _ensure_student(db, student_id)
    data = fetch_subtopic_map_with_pubmed(topic, course)
    if data is None:
        raise HTTPException(status_code=502, detail="LLM failed to produce subtopic map")
    return data


@router.post("/{student_id}/subtopic-map/batch")
def subtopic_map_batch(
    student_id: int,
    course: str = Query(..., description="Course name, applied to all topics"),
    topics: List[str] = Body(..., embed=True, description="List of topic strings"),
    db: Session = Depends(get_db),
):
    """Batch version: returns a dict keyed by topic, each with its subtopic map + PubMed bundle."""
    _ensure_student(db, student_id)
    out: Dict[str, Any] = {}
    for tp in topics:
        node = fetch_subtopic_map_with_pubmed(tp, course)
        if node:
            out[tp] = node
    if not out:
        raise HTTPException(status_code=502, detail="LLM failed for all topics")
    return out
