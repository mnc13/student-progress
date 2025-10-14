from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional

class StudentLogin(BaseModel):
    student_id: int

class CourseOut(BaseModel):
    course: str

class PastItemOut(BaseModel):
    idx: int
    topic: str
    hours: int
    mark: float
    percent: int

class UpcomingEventOut(BaseModel):
    id: int
    idx: int
    course: str
    topic: str
    hours: int
    date: date

class StudyTaskIn(BaseModel):
    title: str
    topic: str
    due_date: date
    hours: int = 1

class StudyTaskOut(BaseModel):
    id: int
    event_idx: int
    course: str
    title: str
    topic: str
    due_date: date
    hours: int
    status: str
    completion_percent: int

class ProgressSummary(BaseModel):
    event_idx: int
    course: str
    topic: str
    due_date: date
    completion_percent: int
    completed_tasks: int
    total_tasks: int

class GeneratePlanResponse(BaseModel):
    created_tasks: List[StudyTaskOut]
