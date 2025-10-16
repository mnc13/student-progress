# app/services/plan.py
from datetime import timedelta, date, datetime
from functools import lru_cache
from typing import List, Dict, Any, Optional
import os
import json
import math
import random
from collections import Counter
import re

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.entities import PastItem, UpcomingEvent, StudyTask
from app.core.config import settings


# -------- LLM / Groq client --------

@lru_cache
def get_groq_client():
    """
    Return a cached Groq client. Raises a clear error if the key isn't set.
    Import happens inside to avoid hard dependency at import time.
    """
    from groq import Groq  # local import to keep module import cheap
    key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("Missing GROQ_API_KEY. Set it in your environment or settings.")
    return Groq(api_key=key)


DEFAULT_MODEL: str = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = (
    "You are a medical education coach. Create concise, actionable study tasks for MBBS students. "
    "Use evidence-based strategies (spaced repetition, active recall, case-based learning, interleaving). "
    "Keep each task specific and time-bounded. Output JSON ONLY following the schema.\n"
    "STRICT RULES:\n"
    "- REQUIRED FIELDS per task: title (<=120 chars), due_date (YYYY-MM-DD), hours (1–3).\n"
    "- OPTIONAL DETAIL FIELDS (encouraged): modality (e.g., 'Anki', 'OSCE drill', 'MCQ timed'), "
    "  focus (key subtopics), resource_hints (short list), deliverable (what to produce), "
    "  practice_count (e.g., number of items/MCQs), notes (1–2 concise lines).\n"
    "- Generate ORIGINAL task titles; avoid boilerplate archetypes repeated across topics.\n"
    "- Vary modalities and subfocus (e.g., nerves/vessels/spaces; radiographs; OSPE/OSCE checklists; diagram redraws).\n"
    "- Organize tasks like a routine: progressive difficulty, alternate modalities (read -> recall -> cases -> MCQs -> refine).\n"
    "- Prefer evenly spaced dates between today and the event date; avoid multiple tasks on the same day unless the event is < 3 days away.\n"
    "- Use MBBS-appropriate verbs and artifacts (Anki/flashcards, OSCE-style cases, MCQs, images/radiographs, diagrams).\n"
    "- Never include commentary, markdown, or code — JSON only.\n"
    "RESPONSE SCHEMA:\n"
    "{ \"tasks\": [ { "
    "\"title\": \"str\", "
    "\"due_date\": \"YYYY-MM-DD\", "
    "\"hours\": 1, "
    "\"modality\": \"str (optional)\", "
    "\"focus\": [\"str\", \"str\"] (optional), "
    "\"resource_hints\": [\"str\", \"str\"] (optional), "
    "\"deliverable\": \"str (optional)\", "
    "\"practice_count\": 30 (optional), "
    "\"notes\": \"str (optional)\" } ] }"
)

# ---- LLM call wrapper ----
def _llm_plan(messages: List[Dict[str, Any]], model_override: Optional[str]) -> List[Dict[str, Any]]:
    """
    Call Groq chat.completions and return a list of tasks (dicts).
    On any failure or bad JSON, return [] so the caller can fallback.
    """
    try:
        client = get_groq_client()
        chosen_model = model_override or DEFAULT_MODEL
        print("Using Groq model:", chosen_model)
    except Exception as e:
        print("Groq client error:", e)
        return []

    try:
        resp = client.chat.completions.create(
            model=chosen_model,
            temperature=0.6,          # more variety while keeping structure
            max_tokens=1600,          # allow richer details
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
    except Exception as e:
        print("Groq completion error:", e)
        return []

    try:
        parsed = json.loads(content or "{}")
        if isinstance(parsed, dict) and isinstance(parsed.get("tasks"), list):
            return parsed["tasks"]
        if isinstance(parsed, list):
            return parsed
    except Exception as e:
        print("JSON parse error:", e)
    return []


def _evenly_spread_dates(n: int, start: date, end: date) -> List[date]:
    """Return n dates from start..end inclusive, roughly evenly spaced and strictly non-decreasing."""
    if start > end:
        start, end = end, start
    if n <= 1:
        return [end]
    total_days = (end - start).days
    if total_days <= 0:
        return [end for _ in range(n)]
    # spread including both ends
    return [start + timedelta(days=round(i * total_days / (n - 1))) for i in range(n)]


def _sanitize_title(t: str, topic: str) -> str:
    t = (t or "").strip()
    if not t:
        return f"Study block: {topic}"
    if len(t) > 120:
        t = t[:118] + "…"
    return t


def _is_mbbs_relevant(title: str) -> bool:
    # very soft heuristic; we only flag obviously generic items
    generic = ["study", "read", "note", "research", "google", "random"]
    return not all(g in title.lower() for g in generic)


def _shorten_with_ellipsis_at_word_boundary(s: str, limit: int) -> str:
    s = (s or "").strip()
    if len(s) <= limit:
        return s
    # keep to nearest previous word boundary to avoid ugly partials
    cut = s[:limit]
    cut = re.sub(r"\W*\w*$", "", cut)  # drop partial trailing word
    if not cut:
        cut = s[:limit]
    return cut + "…"


# ---------- Tag normalization (robust & compact) ----------

_TAG_MAX = 14  # hard cap per tag; if longer, drop the tag entirely (no ellipsis)
_ALLOWED_TAGS = {
    # modality canonicalization
    "anki": "Anki",
    "flash": "Anki",
    "flashcards": "Anki",
    "mcq": "MCQ",
    "quiz": "MCQ",
    "case": "Cases",
    "cases": "Cases",
    "vignette": "Cases",
    "diagram": "Diagram",
    "redraw": "Diagram",
    "osce": "OSCE",
    "ospe": "OSCE",
    "reading": "Reading",
    "read": "Reading",
}

_FOCUS_MAP = {
    # map verbose focus to compact codes
    "high-yield": "HY",
    "high yield": "HY",
    "integrations": "Integrations",
    "stations": "Stations",
    "steps": "Steps",
    "radiographs": "Radiographs",
    "images": "Images",
    "landmarks": "Landmarks",
    "relations": "Relations",
}

_DELIVERABLE_MAP = {
    "concept map": "Concept map",
    "outline": "Outline",
    "checklist": "Checklist",
    "error log": "Error log",
    "notes": "Notes",
    "labeled diagram": "Labeled diagram",
}


def _canon_from_text(text: str) -> Optional[str]:
    t = (text or "").strip().lower()
    if not t:
        return None
    for key, val in _ALLOWED_TAGS.items():
        if key in t:
            return val
    return None


def _compress_focus_tokens(focus: Any, topic: str) -> List[str]:
    """
    Return up to 2 short focus tags.
    - drop tokens that repeat or include the topic
    - ignore tokens with ':' (like 'focus: Clinical Anatomy')
    - map verbose -> compact when possible
    """
    if not isinstance(focus, list):
        return []
    out = []
    topic_l = (topic or "").lower()
    for raw in focus:
        tok = str(raw or "").strip()
        if not tok or ":" in tok:
            continue
        tl = tok.lower()
        if topic_l and (topic_l in tl):
            continue
        # compact mapping
        for k, v in _FOCUS_MAP.items():
            if k in tl:
                tok = v
                break
        # drop overly long focus tokens
        if len(tok) > _TAG_MAX:
            continue
        # dedupe case-insensitive
        if all(tok.lower() != o.lower() for o in out):
            out.append(tok)
        if len(out) >= 2:
            break
    return out


def _deliverable_tag(text: Any) -> Optional[str]:
    t = str(text or "").strip().lower()
    if not t:
        return None
    for k, v in _DELIVERABLE_MAP.items():
        if k in t:
            return v
    # last resort: keep a very short token if it is short enough
    if len(t) <= 10:
        return t.capitalize()
    return None


def _extract_detail_tags(task: Dict[str, Any], topic: str) -> List[str]:
    """
    Convert rich optional fields into compact, standardized tags.
    Rules:
      - Use canonical tags for modality.
      - Practice count attaches to MCQ as 'MCQ xN'; otherwise 'N items'.
      - Focus: up to 2 short tokens, skipping topic and 'focus:' noise.
      - Deliverable: mapped to an approved short tag.
      - No ellipses inside tags; if too long, drop.
      - Max 3 tags total.
    """
    tags: List[str] = []

    # 1) Modality
    modality = str(task.get("modality", "") or "").strip()
    mtag = _canon_from_text(modality)
    if mtag:
        tags.append(mtag)

    # 2) Practice count
    pc = task.get("practice_count")
    pc_int = None
    try:
        if pc is not None:
            pc_int = int(pc)
    except Exception:
        pc_int = None
    if pc_int and pc_int > 0:
        if "MCQ" in tags:
            tags.append(f"x{pc_int}")  # pairs with MCQ
        else:
            # keep short; if too long, drop later
            tags.append(f"{pc_int} items")

    # 3) Focus
    tags.extend(_compress_focus_tokens(task.get("focus"), topic))

    # 4) Deliverable
    dtag = _deliverable_tag(task.get("deliverable"))
    if dtag:
        tags.append(dtag)

    # 5) Filter by length and allowed chars; dedupe
    cleaned: List[str] = []
    seen = set()
    for t in tags:
        t = (t or "").strip()
        if not t:
            continue
        if len(t) > _TAG_MAX:
            continue
        key = t.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(t)

    # 6) Keep order, cap at 3 tags
    return cleaned[:3]


def _enrich_title_with_details(base_title: str, task: Dict[str, Any], topic: str) -> str:
    """
    Add up to 3 compact standardized tags, keeping <=120 chars.
    We only add tags if there's enough room for at least '  [XXXX]'.
    """
    base = _sanitize_title(base_title, topic)
    tags = _extract_detail_tags(task, topic)
    if not tags:
        return base

    # Build suffix incrementally; stop when exceeding 120
    suffix = ""
    for tag in tags:
        candidate = f"{suffix} [{tag}]"
        if len(base) + len(candidate) <= 120:
            suffix = candidate
        else:
            break
    return base + suffix


# ---------- Fallback plan (varied, spaced, with detail fields) ----------

def _fallback_plan(upc: UpcomingEvent, weak_topics: List[str], today: date) -> List[Dict[str, Any]]:
    """
    Rule-based backup when LLM is unavailable or returns invalid JSON.
    Evenly spread tasks from 'today'..'upc.date' (inclusive), vary titles, and weave weak topics.
    Includes optional details that postprocessor can compress into titles.
    """
    end = upc.date
    if end < today:
        end = today

    # decide task count by horizon (aim 4–6)
    horizon = (end - today).days
    n = 6 if horizon >= 10 else 5 if horizon >= 5 else max(4, min(5, horizon + 1))

    topic = upc.topic
    weak_hint = ", ".join([w for w in weak_topics[:2]]) if weak_topics else None

    plan = [
        {
            "title": f"Concept map + core reading: {topic}",
            "modality": "Reading + concept map",
            "focus": [topic],
            "resource_hints": ["BRS/standard text", "class notes"],
            "deliverable": "concept map",
        },
        {
            "title": f"Active recall drill: {topic}",
            "modality": "Anki",
            "focus": ([weak_hint] if weak_hint else []) + ["high-yield"],
            "resource_hints": ["Anki deck", "self-made cloze"],
            "practice_count": 80,
            "deliverable": "notes",
        },
        {
            "title": f"Diagram redraw + labeling: {topic}",
            "modality": "diagram",
            "focus": ["relations", "landmarks"],
            "resource_hints": ["atlas images"],
            "deliverable": "labeled diagram",
        },
        {
            "title": f"Clinical vignettes + images: {topic}",
            "modality": "cases",
            "focus": ["radiographs", "images"],
            "resource_hints": ["case bank", "radiology set"],
            "practice_count": 15,
            "deliverable": "notes",
        },
        {
            "title": f"MCQ set (timed) + error log: {topic}",
            "modality": "MCQ timed",
            "focus": (([weak_hint] if weak_hint else []) + ["integrations"]),
            "resource_hints": ["MCQ bank"],
            "practice_count": 40,
            "deliverable": "error log",
        },
        {
            "title": f"OSCE/OSPE checklist & quick recap: {topic}",
            "modality": "OSCE",
            "focus": ["stations", "steps"],
            "resource_hints": ["OSCE checklist"],
            "deliverable": "checklist",
        },
    ]

    dates = _evenly_spread_dates(n, today, end)

    # hour heuristics (1–3)
    base = max(1, min(3, upc.hours // max(1, n)))
    hours = [max(1, min(3, base)) for _ in range(n)]
    for i, p in enumerate(plan[:n]):
        mm = str(p.get("modality", "")).lower()
        if any(k in mm for k in ["mcq", "case", "osce"]):
            hours[i] = min(3, hours[i] + 1)

    out = []
    for i in range(n):
        item = {
            "title": plan[i]["title"],
            "due_date": dates[i].isoformat(),
            "hours": int(hours[i]),
        }
        item.update({k: v for k, v in plan[i].items() if k not in ["title"]})
        out.append(item)
    return out


# ---------- Post-processing ----------

def _postprocess_tasks(
    raw_tasks: List[Dict[str, Any]],
    upc: UpcomingEvent,
    today: date,
) -> List[Dict[str, Any]]:
    """
    Enforce:
    - 4–6 tasks
    - hours 1–3 (int)
    - due_date clamped between today and event date
    - titles unique, short, original-ish
    - routine spacing if clustered
    - integrate optional detail fields into titles as compact, standardized tags (no ellipses)
    """
    if not raw_tasks:
        return []

    # 1) Coerce + basic validation
    coerced: List[Dict[str, Any]] = []
    for t in raw_tasks:
        try:
            base_title = str(t.get("title", ""))
            title = _enrich_title_with_details(_sanitize_title(base_title, upc.topic), t, upc.topic)
            hours = int(t.get("hours", 1))
            hours = max(1, min(3, hours))
            due_s = str(t.get("due_date", upc.date.isoformat()))
            d = date.fromisoformat(due_s[:10])  # accept date or datetime
        except Exception:
            d = upc.date
            title = _sanitize_title("Study block", upc.topic)
            hours = 1

        # clamp date
        if d < today:
            d = today
        if d > upc.date:
            d = upc.date

        coerced.append({"title": title, "due_date": d, "hours": hours})

    # 2) Enforce count 4–6
    if len(coerced) < 4:
        pads_needed = 4 - len(coerced)
        scaffold = [
            "Active recall (flashcards)",
            "Image review & labeling",
            "MCQ set + error log",
            "Case vignette walkthrough",
        ]
        for i in range(pads_needed):
            coerced.append(
                {
                    "title": f"{scaffold[i % len(scaffold)]}: {upc.topic}",
                    "due_date": upc.date,
                    "hours": 1,
                }
            )
    elif len(coerced) > 6:
        coerced = coerced[:6]

    # 3) De-duplicate titles (light normalization)
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for t in coerced:
        key = t["title"].strip().lower()
        if key in seen or key == upc.topic.strip().lower():
            suffix = random.choice([" (recall)", " (MCQs)", " (cases)", " (diagram)"])
            new_title = (t["title"] + suffix)[:120]
            key = new_title.strip().lower()
            t["title"] = new_title
        if key not in seen:
            seen.add(key)
            uniq.append(t)
    coerced = uniq

    # 4) Force routine spacing if dates are too clustered
    dates = [t["due_date"] for t in coerced]
    counts = Counter(dates)
    # re-spread if ANY duplicate day exists OR if we have fewer than (len(coerced) - 1) unique days
    if any(c > 1 for c in counts.values()) or len(counts) < len(coerced) - 1:
        spread = _evenly_spread_dates(len(coerced), today, upc.date)
        # stable mapping so titles/dates look intentional
        for i, t in enumerate(sorted(coerced, key=lambda x: (x["due_date"], x["title"]))):
            t["due_date"] = spread[i]

    # 5) Soft MBBS relevance nudges
    for t in coerced:
        if not _is_mbbs_relevant(t["title"]):
            t["title"] = f"Clinically-applied study: {upc.topic} (MCQs + cases)"

    # 6) Final coerce to serializable dicts
    finalized = [
        {"title": t["title"], "due_date": t["due_date"].isoformat(), "hours": int(t["hours"])}
        for t in coerced
    ]
    return finalized


def generate_study_tasks(
    db: Session,
    student_id: int,
    course: str,
    model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate tasks ONLY for the selected course. Idempotent per event.
    Returns a list of plain dicts (serialized before commit) to avoid
    SQLAlchemy ObjectDeletedError / expired attributes issues.
    """
    today = date.today()

    # Upcoming events for this course
    upcomings = db.scalars(
        select(UpcomingEvent).where(
            UpcomingEvent.student_id == student_id,
            UpcomingEvent.course == course,
        )
    ).all()

    # Weak topics for this course
    past = db.scalars(
        select(PastItem).where(
            PastItem.student_id == student_id,
            PastItem.course == course,
        )
    ).all()
    weak_topics = [p.topic for p in past if getattr(p, "mark", 0) < 0.5]

    created_tasks: List[StudyTask] = []

    for upc in upcomings:
        # ---- Idempotency: skip if tasks already exist for this event ----
        existing = db.scalars(
            select(StudyTask).where(
                and_(
                    StudyTask.student_id == student_id,
                    StudyTask.course == upc.course,
                    StudyTask.event_idx == upc.idx,
                )
            )
        ).first()
        if existing:
            # already generated for this event; skip creating duplicates
            continue

        user_prompt = {
            "role": "user",
            "content": f"""
Student is preparing for upcoming topic "{upc.topic}" in the course "{upc.course}" on {upc.date}.
They have approximately {upc.hours} study hours in total before the event.
Historically weak topics for this course: {", ".join(weak_topics) if weak_topics else "None"}.

Create 4–6 granular tasks with:
- REQUIRED: "title" (<=120 chars, ORIGINAL), "due_date" (YYYY-MM-DD, strictly between today ({today}) and the event date ({upc.date})), "hours" (integer 1–3).
- OPTIONAL (encouraged): "modality", "focus" (list), "resource_hints" (list), "deliverable", "practice_count", "notes".
- Avoid placing multiple tasks on the same calendar day unless {upc.date} is within 3 days of {today}.
- Spread like a routine (progression + interleaving), and tie at least one task directly to historically weak topics if any.

Prioritize MBBS relevance (anatomy, physiology, pathology, pharmacology, micro, community medicine, OSCE/OSPE where relevant).
Encourage active recall (flashcards/Anki), spaced repetition, case images/radiographs, and MCQs with error logging.

Respond with JSON ONLY in this exact schema:
{{ "tasks": [ {{ "title": "str", "due_date": "YYYY-MM-DD", "hours": 1, "modality": "str (optional)", "focus": ["str"], "resource_hints": ["str"], "deliverable": "str", "practice_count": 30, "notes": "str" }} ] }}
""".strip(),
        }

        raw_tasks = _llm_plan([{"role": "system", "content": SYSTEM_PROMPT}, user_prompt], model)
        print("LLM returned tasks:", raw_tasks)
        if not raw_tasks:
            raw_tasks = _fallback_plan(upc, weak_topics, today)

        tasks_json = _postprocess_tasks(raw_tasks, upc, today)

        for t in tasks_json:
            # Validate again and coerce (defensive)
            try:
                due = date.fromisoformat(str(t["due_date"])[:10])
                # clamp once more
                if due < today:
                    due = today
                if due > upc.date:
                    due = upc.date
                hours = int(t.get("hours", 1))
                hours = max(1, min(3, hours))
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
            db.flush()  # assign id, etc.
            created_tasks.append(task)

    # ---- Serialize BEFORE commit (prevents expired/refresh issues) ----
    payload: List[Dict[str, Any]] = [
        {
            "id": t.id,
            "student_id": t.student_id,
            "course": t.course,
            "event_idx": t.event_idx,
            "title": t.title,
            "topic": t.topic,
            "due_date": t.due_date.isoformat(),
            "hours": t.hours,
            "status": t.status,
            "completion_percent": t.completion_percent,
        }
        for t in created_tasks
    ]

    db.commit()
    return payload
