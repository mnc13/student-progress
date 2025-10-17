# app/models/entities.py
from sqlalchemy import Boolean, Column, Integer, String, Date, Float
from .db import Base

class Student(Base):
    __tablename__ = "students"
    student_id = Column(Integer, primary_key=True, index=True)

class PastItem(Base):
    __tablename__ = "past_items"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, index=True, nullable=False)
    course = Column(String, index=True, nullable=False)
    idx = Column(Integer, nullable=False)
    topic = Column(String, nullable=False)
    hours = Column(Integer, nullable=False)
    mark = Column(Float, nullable=False)

class UpcomingEvent(Base):
    __tablename__ = "upcoming_events"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, index=True, nullable=False)
    course = Column(String, index=True, nullable=False)
    idx = Column(Integer, nullable=False)
    topic = Column(String, nullable=False)
    hours = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    is_final = Column(Boolean, nullable=False, default=False, server_default="0")

class StudyTask(Base):
    __tablename__ = "study_tasks"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, index=True, nullable=False)
    course = Column(String, index=True, nullable=False)
    event_idx = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    due_date = Column(Date, nullable=False)
    hours = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="not_started")
    completion_percent = Column(Integer, nullable=False, default=0)
