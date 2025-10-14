from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
import pandas as pd
from pathlib import Path
from sqlalchemy import text
from app.models.entities import Student, PastItem, UpcomingEvent

def bootstrap_from_csv(db: Session, csv_path: Path) -> None:
    """
    Load initial student, past item, and upcoming event data from CSV.
    This version is safe to run multiple times (idempotent).
    """

    df = pd.read_csv(csv_path)

    past_idx = [1, 2, 3, 4, 5]
    upc_idx = [6, 7, 8, 9, 10]

    existing_students = set(
        r[0] for r in db.execute(text("SELECT student_id FROM students")).fetchall()
    )

    for _, row in df.iterrows():
        sid = int(row["studentID"])
        course = str(row["course"])

        # ✅ Add student only if not already in DB or pending session
        if sid not in existing_students:
            db.add(Student(student_id=sid))
            existing_students.add(sid)

        # 🧠 Add Past Items
        for i in past_idx:
            mark = float(row.get(f"item{i}", 0.0))
            topic = str(row.get(f"item{i}_topic", "")).strip()
            hours = int(row.get(f"item{i}_hours", 0))
            if topic and hours > 0:
                exists = db.scalar(
                    select(PastItem).where(
                        PastItem.student_id == sid,
                        PastItem.course == course,
                        PastItem.idx == i,
                    )
                )
                if not exists:
                    db.add(
                        PastItem(
                            student_id=sid,
                            course=course,
                            idx=i,
                            topic=topic,
                            hours=hours,
                            mark=mark,
                        )
                    )

        # 📅 Add Upcoming Events
        for j in upc_idx:
            topic = str(row.get(f"upc_item{j}_topic", "")).strip()
            hours_val = row.get(f"upc_item{j}_hours", 0)
            hours = int(hours_val) if not pd.isna(hours_val) else 0
            date_str = row.get(f"upc_item{j}_date", "")

            if topic and hours > 0 and date_str:
                try:
                    d = datetime.fromisoformat(str(date_str)).date()
                except Exception:
                    continue

                exists = db.scalar(
                    select(UpcomingEvent).where(
                        UpcomingEvent.student_id == sid,
                        UpcomingEvent.course == course,
                        UpcomingEvent.idx == j,
                    )
                )
                if not exists:
                    db.add(
                        UpcomingEvent(
                            student_id=sid,
                            course=course,
                            idx=j,
                            topic=topic,
                            hours=hours,
                            date=d,
                        )
                    )

    db.commit()
    print("[INFO] ✅ CSV bootstrap completed successfully.")
