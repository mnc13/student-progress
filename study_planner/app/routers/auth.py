from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.db import SessionLocal
from app.models.entities import Student
from app.models.schemas import StudentLogin

router = APIRouter(prefix="/auth", tags=["auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login")
def login(payload: StudentLogin, db: Session = Depends(get_db)):
    student = db.scalar(select(Student).where(Student.student_id == payload.student_id))
    if not student:
        raise HTTPException(status_code=404, detail="student_id not found")
    return {"ok": True, "student_id": payload.student_id}
