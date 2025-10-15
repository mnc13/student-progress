from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case

from app.models.db import SessionLocal
from app.models.entities import Student, PastItem, UpcomingEvent, StudyTask
from app.models.schemas import (
    CourseOut, PastItemOut, UpcomingEventOut, StudyTaskOut, GeneratePlanResponse, ProgressSummary
)
from app.services.plan import generate_study_tasks

router = APIRouter(prefix="/students", tags=["students"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _ensure_student(db: Session, student_id: int):
    if not db.scalar(select(Student).where(Student.student_id == student_id)):
        raise HTTPException(status_code=404, detail="student_id not found")

@router.get("/{student_id}/courses", response_model=List[CourseOut])
def list_courses(student_id: int, db: Session = Depends(get_db)):
    _ensure_student(db, student_id)
    rows = db.execute(select(PastItem.course).where(PastItem.student_id == student_id).distinct()).all()
    return [{"course": r[0]} for r in rows]

@router.get("/{student_id}/courses/{course}/past", response_model=List[PastItemOut])
def past_items(student_id: int, course: str, db: Session = Depends(get_db)):
    _ensure_student(db, student_id)
    items = db.scalars(select(PastItem).where(PastItem.student_id == student_id, PastItem.course == course).order_by(PastItem.idx)).all()
    out = []
    for it in items:
        out.append({
            "idx": it.idx,
            "topic": it.topic,
            "hours": it.hours,
            "mark": it.mark,
            "percent": int(round(it.mark * 100))
        })
    return out

@router.get("/{student_id}/upcoming", response_model=List[UpcomingEventOut])
def upcoming(student_id: int, db: Session = Depends(get_db)):
    _ensure_student(db, student_id)
    events = db.scalars(select(UpcomingEvent).where(UpcomingEvent.student_id == student_id).order_by(UpcomingEvent.date)).all()
    return [{
        "id": ev.id, "idx": ev.idx, "course": ev.course, "topic": ev.topic, "hours": ev.hours, "date": ev.date
    } for ev in events]

@router.post("/{student_id}/study-plan/generate", response_model=GeneratePlanResponse)
def generate_plan(student_id: int, db: Session = Depends(get_db)):
    _ensure_student(db, student_id)
    created = generate_study_tasks(db, student_id)
    return {"created_tasks": [{
        "id": t.id, "event_idx": t.event_idx, "course": t.course, "title": t.title, "topic": t.topic,
        "due_date": t.due_date, "hours": t.hours, "status": t.status, "completion_percent": t.completion_percent
    } for t in created]}

@router.get("/{student_id}/tasks", response_model=List[StudyTaskOut])
def list_tasks(student_id: int, db: Session = Depends(get_db)):
    _ensure_student(db, student_id)
    tasks = db.scalars(select(StudyTask).where(StudyTask.student_id == student_id).order_by(StudyTask.due_date)).all()
    return [{
        "id": t.id, "event_idx": t.event_idx, "course": t.course, "title": t.title, "topic": t.topic,
        "due_date": t.due_date, "hours": t.hours, "status": t.status, "completion_percent": t.completion_percent
    } for t in tasks]

@router.patch("/{student_id}/tasks/{task_id}", response_model=StudyTaskOut)
def update_task(student_id: int, task_id: int, status: str | None = None, completion_percent: int | None = None, db: Session = Depends(get_db)):
    _ensure_student(db, student_id)
    t = db.get(StudyTask, task_id)
    if not t or t.student_id != student_id:
        raise HTTPException(status_code=404, detail="task not found")
    changed = False
    if status:
        if status not in {"not_started", "in_progress", "done"}:
            raise HTTPException(status_code=400, detail="invalid status")
        t.status = status
        if status == "done":
            t.completion_percent = 100
        changed = True
    if completion_percent is not None:
        if not (0 <= completion_percent <= 100):
            raise HTTPException(status_code=400, detail="invalid completion_percent")
        t.completion_percent = completion_percent
        if completion_percent == 100:
            t.status = "done"
        elif completion_percent > 0 and t.status == "not_started":
            t.status = "in_progress"
        changed = True
    if changed:
        db.add(t); db.commit(); db.refresh(t)
    return {
        "id": t.id, "event_idx": t.event_idx, "course": t.course, "title": t.title, "topic": t.topic,
        "due_date": t.due_date, "hours": t.hours, "status": t.status, "completion_percent": t.completion_percent
    }

@router.get("/{student_id}/progress", response_model=List[ProgressSummary])
def progress(student_id: int, db: Session = Depends(get_db)):
    _ensure_student(db, student_id)
    rows = db.execute(
        select(
            StudyTask.event_idx,
            StudyTask.course,
            StudyTask.topic,
            StudyTask.due_date,
            func.coalesce(func.avg(StudyTask.completion_percent), 0).label("avg_pct"),
            func.count(StudyTask.id).label("cnt"),
            func.sum(case((StudyTask.status == "done", 1), else_=0)).label("done_cnt"),
        )
        .where(StudyTask.student_id == student_id)
        .group_by(StudyTask.event_idx, StudyTask.course, StudyTask.topic, StudyTask.due_date)
    ).all()

    out = []
    for r in rows:
        out.append({
            "event_idx": r[0],
            "course": r[1],
            "topic": r[2],
            "due_date": r[3],
            "completion_percent": int(round(r[4] or 0)),
            "completed_tasks": int(r[6] or 0),
            "total_tasks": int(r[5] or 0),
        })
    return out
