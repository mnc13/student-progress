# app/utils/csv_loader.py
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.entities import Student, PastItem, UpcomingEvent

# Accept multiple date formats, including common regional ones
_DATE_FMTS: list[str] = [
    "%Y-%m-%d",  # ISO
    "%m/%d/%Y",  # US
    "%d/%m/%Y",  # EU
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%m-%d-%Y",
]


def _parse_date(s: str | None) -> Optional[date]:
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def _get_first_present(row: dict, *keys: str, default=None):
    """Return row[key] for the first present key (case-sensitive), else default."""
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return default


def _safe_int(v, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        try:
            # Sometimes numeric strings come as floats like "29.0"
            return int(float(v))
        except Exception:
            return default


def _safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


@dataclass
class _DetectedDialect:
    delimiter: str = ","


def _detect_dialect(sample: str) -> _DetectedDialect:
    # Prefer tab if tabs exist in the first line (common for spreadsheets copied as TSV)
    if "\t" in sample.splitlines()[0]:
        return _DetectedDialect(delimiter="\t")
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=",\t;|")
        return _DetectedDialect(delimiter=dialect.delimiter)
    except Exception:
        return _DetectedDialect()


def _read_rows(csv_path: Path) -> list[dict]:
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        head = f.read(4096)
        f.seek(0)
        dialect = _detect_dialect(head)
        reader = csv.DictReader(f, delimiter=dialect.delimiter)
        return list(reader)


def bootstrap_from_csv(db: Session, csv_path: Path) -> None:
    """
    Idempotent-ish bootstrapper that:
      1) Ensures Student rows exist
      2) Inserts PastItem rows (indices start at 1 in CSV order)
      3) Inserts UpcomingEvent rows from upc_item{n}_* sets
      4) Inserts a single final exam if item_final_date exists

    Columns supported (case-sensitive, choose any compatible schema described below):
      - student_id or studentID
      - course (Course)
      - Past item schemas:
          A) item{i}, item{i}_topic, item{i}_hours
          B) past_item{i}_topic, past_item{i}_hours, past_item{i}_mark
      - Upcoming items: upc_item{j}_topic, upc_item{j}_hours, upc_item{j}_date
      - Final: item_final_date

    Delimiter is auto-detected (CSV/TSV/semicolon). Dates support multiple formats.
    """
    if not csv_path.exists():
        return

    rows = _read_rows(csv_path)
    if not rows:
        return

    # ---------- Students ----------
    seen: set[int] = set()
    for r in rows:
        sid_val = _get_first_present(r, "student_id", "studentID")
        if sid_val is None:
            continue
        sid = _safe_int(sid_val, default=-1)
        if sid < 0 or sid in seen:
            continue
        if not db.scalar(select(Student).where(Student.student_id == sid)):
            db.add(Student(student_id=sid))
        seen.add(sid)
    db.commit()

    # ---------- Per row: past items, upcoming, final ----------
    for r in rows:
        sid_val = _get_first_present(r, "student_id", "studentID")
        if sid_val is None:
            continue
        sid = _safe_int(sid_val, default=-1)
        if sid < 0:
            continue

        course = str(_get_first_present(r, "course", "Course", default="")).strip()
        if not course:
            continue

        # ---- PAST items ----
        # Accept both schemas (A/B)
        i = 1
        while True:
            # schema A
            markA = _get_first_present(r, f"item{i}")
            topicA = _get_first_present(r, f"item{i}_topic")
            hrsA = _get_first_present(r, f"item{i}_hours")

            # schema B
            topicB = _get_first_present(r, f"past_item{i}_topic")
            hrsB = _get_first_present(r, f"past_item{i}_hours")
            markB = _get_first_present(r, f"past_item{i}_mark")

            if topicA is None and topicB is None:
                # stop when neither A nor B exists
                if (f"item{i}_topic" not in r) and (f"past_item{i}_topic" not in r):
                    break
                else:
                    i += 1
                    continue

            topic = str(topicA if topicA is not None else topicB).strip()
            if not topic:
                i += 1
                continue

            hours = _safe_int(hrsA if hrsA is not None else hrsB, default=0)
            mark = _safe_float(markA if markA is not None else markB, default=0.0)

            db.add(
                PastItem(
                    student_id=sid, course=course, idx=i, topic=topic, hours=hours, mark=mark
                )
            )
            i += 1

        # ---- UPCOMING items (schema: upc_item{j}_topic/hours/date) ----
        j = 1
        last_idx = 0
        while True:
            tkey = f"upc_item{j}_topic"
            hkey = f"upc_item{j}_hours"
            dkey = f"upc_item{j}_date"
            if (tkey not in r) and (hkey not in r) and (dkey not in r):
                if j > 50:  # safety upper bound
                    break
                j += 1
                continue

            topic = str(_get_first_present(r, tkey, default="") or "").strip()
            if not topic:
                j += 1
                continue

            hrs = _safe_int(_get_first_present(r, hkey, default=0) or 0, default=0)
            dt = _parse_date(_get_first_present(r, dkey))
            if dt:
                db.add(
                    UpcomingEvent(
                        student_id=sid,
                        course=course,
                        idx=j,
                        topic=topic,
                        hours=max(1, hrs),
                        date=dt,
                        is_final=False,
                    )
                )
                last_idx = j
            j += 1

        # ---- FINAL exam (single column: item_final_date) ----
        final_dt = _parse_date(_get_first_present(r, "item_final_date"))
        if final_dt:
            db.add(
                UpcomingEvent(
                    student_id=sid,
                    course=course,
                    idx=(last_idx + 1) if last_idx else 999,
                    topic="Final Assessment",
                    hours=0,  # hours will be allocated by LLM later
                    date=final_dt,
                    is_final=True,
                )
            )

    db.commit()