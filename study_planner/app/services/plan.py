from __future__ import annotations

"""
app/services/plan.py

Unified planning module:
- Groq / LLM initialization tolerant to deprecation or missing key
- JSON prompt + retry + fallback logic
- Topic-plan prompt with basics / focus / study_path
- Fallback task generator
- Task persistence & enrichment logic
"""

from datetime import timedelta, date
from typing import List, Dict, Any, Optional
import logging
from urllib.parse import quote_plus

from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.models.entities import PastItem, UpcomingEvent, StudyTask
from app.core.config import settings

log = logging.getLogger(__name__)

# --- Patch internal Groq httpx wrappers to drop unsupported "proxies" kwarg ---
try:
    from groq._base_client import SyncHttpxClientWrapper
    _orig_init = SyncHttpxClientWrapper.__init__

    def _patched_init(self, *args, **kwargs):
        kwargs.pop("proxies", None)
        return _orig_init(self, *args, **kwargs)

    SyncHttpxClientWrapper.__init__ = _patched_init
except Exception:
    pass

# --- Groq client init ---
_client = None
def _init_groq_client():
    global _client
    if not settings.HAS_GROQ:
        _client = None
        return
    try:
        from groq import Groq
        _client = Groq(api_key=settings.GROQ_API_KEY)
        log.info("[LLM] Groq client initialized.")
    except Exception as e:
        log.error("[LLM] initialization error: %s", e, exc_info=True)
        _client = None

_init_groq_client()

DEFAULT_MODEL = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")

# --- Prompts ---
SYSTEM_TASK_PROMPT = (
    "You are a medical education coach for MBBS students. "
    "Create concise, actionable tasks using evidence-based strategies (active recall, cases, MCQs). "
    "Output strict JSON."
)
SYSTEM_ENRICH_PROMPT = (
    "You are an MBBS content curator. For each topic, list 4-8 high-yield subtopics and 3-6 trusted resources (title, url, kind). "
    "Return strict JSON."
)
SYSTEM_SUBTOPIC_MAP = (
    "You are an MBBS academic coach. Extract exam-relevant subtopics and build a stepwise study map (modality, action, deliverable, time). "
    "Return STRICT JSON, no commentary."
)

def _chat_json(messages: List[Dict[str, Any]], *, max_tokens: int = 2000) -> Optional[Dict[str, Any]]:
    if _client is None:
        return None
    try:
        resp = _client.chat.completions.create(
            model=DEFAULT_MODEL,
            temperature=0.2,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=messages,
        )
        content = resp.choices[0].message.content
    except Exception as e:
        log.error("[LLM] chat failed: %s", e, exc_info=True)
        return None

    import json
    try:
        return json.loads(content)
    except Exception as e:
        log.error("[LLM] JSON parse failed: %s — content: %s", e, content, exc_info=True)
        return None

# --- PubMed & URL helpers ---
def _pubmed_search_url(query: str, *, filters: Optional[Dict[str, str]] = None) -> str:
    base = "https://pubmed.ncbi.nlm.nih.gov/?term="
    url = base + quote_plus(query)
    if filters:
        for k, v in filters.items():
            url += f"&{quote_plus(k)}={quote_plus(v)}"
    return url

def _pubmed_esearch_url(query: str, *, retmax: int = 100) -> str:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = f"?db=pubmed&retmode=json&retmax={retmax}&term={quote_plus(query)}"
    return base + params

def _mesh_browse_url(term: str) -> str:
    return "https://meshb.nlm.nih.gov/search?query=" + quote_plus(term)

def _bookshelf_search_url(q: str) -> str:
    return "https://www.ncbi.nlm.nih.gov/books/?term=" + quote_plus(q)

def _radiopaedia_search_url(q: str) -> str:
    return "https://radiopaedia.org/search?lang=us&q=" + quote_plus(q)

def _build_pubmed_queries(topic: str, subtopics: List[str]) -> Dict[str, Any]:
    topic_q = topic.strip()
    base_q = f"({topic_q})"
    recent = {"filter": "years.5"}
    bundle: Dict[str, Any] = {
        "topic": topic_q,
        "overview": {
            "pubmed_ui": _pubmed_search_url(base_q, filters=recent),
            "pubmed_esearch": _pubmed_esearch_url(base_q),
            "mesh": _mesh_browse_url(topic_q),
            "bookshelf": _bookshelf_search_url(topic_q),
        },
        "angles": {
            "reviews": _pubmed_search_url(f"{base_q} AND (review[Publication Type])", filters=recent),
            "guidelines": _pubmed_search_url(f"{base_q} AND (guideline[Publication Type])", filters=recent),
            "imaging": _pubmed_search_url(f"{base_q} AND (diagnostic imaging[MeSH Terms])", filters=recent),
        },
        "by_subtopic": [],
        "adjacent": {"radiopaedia": _radiopaedia_search_url(topic_q)}
    }
    for st in (subtopics or [])[:10]:
        stq = st.strip()
        if not stq:
            continue
        q = f'("{topic_q}") AND ("{stq}"[Title/Abstract] OR "{stq}"[MeSH Terms])'
        bundle["by_subtopic"].append({
            "subtopic": stq,
            "pubmed_ui": _pubmed_search_url(q, filters=recent),
            "pubmed_esearch": _pubmed_esearch_url(q),
            "mesh": _mesh_browse_url(stq),
        })
    return bundle

# --- Fallback plan for tasks ---
def _fallback_plan(upc: UpcomingEvent, weak_topics: List[str]) -> List[Dict[str, Any]]:
    log.info("[LLM] using fallback plan for %s", upc.topic)
    due = upc.date
    blocks = [
        {"title": f"Read core concepts of {upc.topic}", "days_before": 7, "hours": max(1, upc.hours//5)},
        {"title": f"Active recall: {upc.topic}", "days_before": 5, "hours": max(1, upc.hours//6)},
        {"title": f"Case studies & images: {upc.topic}", "days_before": 3, "hours": max(1, upc.hours//6)},
        {"title": f"MCQ practice & review: {upc.topic}", "days_before": 2, "hours": max(1, upc.hours//6)},
        {"title": f"Final summary & test: {upc.topic}", "days_before": 0, "hours": 1},
    ]
    if weak_topics:
        blocks.insert(1, {
            "title": f"Remediate weak: {', '.join(weak_topics[:2])}",
            "days_before": 6,
            "hours": 2
        })
    tasks: List[Dict[str, Any]] = []
    for b in blocks:
        d = (due - timedelta(days=b["days_before"])).isoformat()
        tasks.append({"title": b["title"], "due_date": d, "hours": b["hours"], "topic": upc.topic})
    return tasks

# --- New: LLM topic plan with “basics / focus / study_path” prompt ---
def _llm_topic_plan_with_path(
    upc: UpcomingEvent, weak_topics: List[str]
) -> List[Dict[str, Any]]:
    # Build the prompt
    user = {
        "role": "user",
        "content": f"""
You are a medical education coach.  

Topic: "{upc.topic}"
Historically weak subtopics: {', '.join(weak_topics)}  

Produce EXACT JSON with this schema (no extra keys):
{{
  "topic": "str",
  "basics": ["str", ...],
  "focus": ["str", ...],
  "study_path": [
    {{
      "step": 1,
      "modality": "Active Recall",
      "target": "str",
      "deliverable": "str"
    }},
    {{
      "step": 2,
      "modality": "Case-based Learning",
      "target": "str",
      "deliverable": "str"
    }},
    {{
      "step": 3,
      "modality": "MCQ Practice",
      "target": "str",
      "deliverable": "str"
    }},
    {{
      "step": 4,
      "modality": "Review",
      "target": "str",
      "deliverable": "str"
    }}
  ]
}}
"""
    }
    messages = [{"role": "system", "content": SYSTEM_TASK_PROMPT}, user]

    data = _chat_json(messages)
    if not (isinstance(data, dict) and "study_path" in data and "basics" in data):
        log.warning("[LLM] detailed plan with path failed for %s, fallback to simpler plan", upc.topic)
        return []  # fallback upstream will handle

    # Translate study_path into tasks
    tasks: List[Dict[str, Any]] = []
    for step in data["study_path"]:
        mod = step.get("modality")
        tgt = step.get("target")
        title = f"{mod}: {tgt}" if tgt else mod
        tasks.append({
            "title": title,
            "topic": upc.topic,
            "modality": mod,
            "focus": [tgt] if tgt else []
        })
    return tasks

# --- Existing LLM topic plan (fallback) ---
def _llm_topic_plan(upc: UpcomingEvent, weak_topics: List[str]) -> List[Dict[str, Any]]:
    messages = [
        {"role": "system", "content": SYSTEM_TASK_PROMPT},
        {
            "role": "user",
            "content": f"""
Create a short study plan for topic "{upc.topic}". Available hours: {upc.hours}. Weak topics: {', '.join(weak_topics)}.

Output strict JSON:
{{ "tasks": [ {{ "title":"str", "topic":"str", "due_date":"YYYY-MM-DD", "hours": int, "subtopics":["str"], "resources":[{{"title","url","kind"}}] }} ] }}
"""
        },
    ]
    data = _chat_json(messages)
    if not data or "tasks" not in data or not isinstance(data["tasks"], list):
        return []
    tasks: List[Dict[str, Any]] = []
    for t in data["tasks"]:
        try:
            due = t["due_date"]
            hrs = int(t.get("hours", 1))
            title = t["title"]
            sub = list(t.get("subtopics", []))
            res = list(t.get("resources", []))
            tasks.append({
                "title": title,
                "topic": upc.topic,
                "due_date": due,
                "hours": hrs,
                "subtopics": sub,
                "resources": res,
            })
        except Exception:
            continue
    return tasks

# --- Persist tasks to DB + orchestration ---
def generate_study_tasks(
    db: Session,
    student_id: int,
    course: str,
    *,
    final_only: bool = False,
    use_llm: bool = True
) -> List[StudyTask]:
    upcs = db.scalars(
        select(UpcomingEvent).where(
            UpcomingEvent.student_id == student_id,
            UpcomingEvent.course == course,
        )
    ).all()

    past = db.scalars(
        select(PastItem).where(PastItem.student_id == student_id, PastItem.course == course)
    ).all()
    weak = [p.topic for p in past if (p.mark or 0.0) < 0.5]

    created: List[StudyTask] = []
    if use_llm and _client is None:
        raise RuntimeError("LLM requested but not configured")

    for upc in upcs:
        db.execute(delete(StudyTask).where(
            StudyTask.student_id == student_id,
            StudyTask.course == course,
            StudyTask.event_idx == upc.idx
        ))

        # Try new detailed variant first
        tasks_json = []
        if use_llm:
            tasks_json = _llm_topic_plan_with_path(upc, weak)
            if not tasks_json:
                log.info("[LLM] fallback to simpler topic plan for %s", upc.topic)
                tasks_json = _llm_topic_plan(upc, weak)
            if not tasks_json:
                log.warning("[LLM] no tasks via LLM for %s; fallback plan", upc.topic)

        if not tasks_json:
            tasks_json = _fallback_plan(upc, weak)

        # Postprocess & persist
        for t in tasks_json:
            try:
                due = date.fromisoformat(str(t.get("due_date", upc.date.isoformat())))
            except Exception:
                due = upc.date
            hrs = int(t.get("hours", 1) or 1)
            title = str(t.get("title", ""))[:200]
            topic_for_row = (t.get("topic") or upc.topic)[:120]
            row = StudyTask(
                student_id=student_id,
                course=course,
                event_idx=upc.idx,
                title=title,
                topic=topic_for_row,
                due_date=due,
                hours=hrs,
                status="not_started",
                completion_percent=0,
            )
            db.add(row)
            created.append(row)

    db.commit()
    return created

# --- Enrichment with fallback for JSON errors ---
def fetch_topic_enrichment(course: str, topics: List[str]) -> Dict[str, Dict[str, Any]]:
    import json
    if _client is None:
        # fallback deterministic
        out: Dict[str, Dict[str, Any]] = {}
        for t in topics:
            subs = [f"{t}: core concepts", f"{t}: clinical relevance", f"{t}: imaging", f"{t}: MCQ pitfalls"]
            res = [
                {"title": f"{t} overview", "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={t.replace(' ', '%20')}", "kind": "article"},
                {"title": f"{t} lecture", "url": f"https://www.youtube.com/results?search_query={t.replace(' ', '+')}+mbbs", "kind": "video"},
            ]
            out[t] = {"subtopics": subs, "resources": res}
            out[t]["pubmed"] = _build_pubmed_queries(t, subs)
        return out

    user = {
        "role": "user",
        "content": (
            "You are an expert MBBS content curator. Topics: " + ", ".join(topics) +
            "\nReturn strict JSON mapping each topic to {subtopics: [..], resources: [..]}. "\
            "4-8 subtopics and 3-6 resources each. No commentary."
        )
    }
    messages = [{"role": "system", "content": SYSTEM_ENRICH_PROMPT}, user]

    parsed = _chat_json(messages)
    if parsed is None:
        log.warning("[LLM] enrichment JSON failed, using fallback for %s", topics)
        return fetch_topic_enrichment(course, topics)  # recursion but will go fallback path if _client is None

    out: Dict[str, Dict[str, Any]] = {}
    for t in topics:
        node = parsed.get(t)
        if not isinstance(node, dict):
            subs = [f"{t}: core concepts", f"{t}: MCQ pitfalls"]
            res = [{"title": f"{t} fallback", "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={t.replace(' ', '%20')}", "kind": "article"}]
            out[t] = {"subtopics": subs, "resources": res}
        else:
            subs = [str(s) for s in node.get("subtopics", [])][:8]
            clean_res: List[Dict[str, str]] = []
            for r in (node.get("resources") or [])[:6]:
                try:
                    clean_res.append({
                        "title": str(r.get("title", ""))[:200],
                        "url": str(r.get("url", "")),
                        "kind": str(r.get("kind", "site")).lower(),
                    })
                except Exception:
                    continue
            out[t] = {"subtopics": subs, "resources": clean_res}
        out[t]["pubmed"] = _build_pubmed_queries(t, out[t]["subtopics"])
    return out

# --- Subtopic map endpoints ---
def subtopic_map_user_prompt(topic: str, course: str) -> Dict[str, str]:
    return {
        "role": "user",
        "content": f"""
Course: {course}
Topic: {topic}

Produce STRICT JSON:
{{
  "topic": "str",
  "subtopics": [ {{ "section":"str", "items":["str", ...] }} ],
  "study_path": [ {{ "step":1, "title":"str","modality":"Reading|Anki|MCQ|Cases|OSCE", "action":"str", "deliverable":"str", "time_box_hours":1 }} ],
  "resource_hints": ["str", ...]
}}
"""
    }

def fetch_subtopic_map(topic: str, course: str) -> Optional[Dict[str, Any]]:
    data = _chat_json([{"role": "system", "content": SYSTEM_SUBTOPIC_MAP}, subtopic_map_user_prompt(topic, course)],
                      max_tokens=1400)
    if not isinstance(data, dict):
        log.warning("[LLM] subtopic_map JSON invalid for %s", topic)
        return None
    data["topic"] = str(data.get("topic", topic))[:200]
    data["subtopics"] = data.get("subtopics", [])
    data["study_path"] = data.get("study_path", [])
    data["resource_hints"] = data.get("resource_hints", [])
    return data

def fetch_subtopic_map_with_pubmed(topic: str, course: str) -> Optional[Dict[str, Any]]:
    m = fetch_subtopic_map(topic, course)
    if not m:
        return None
    sub_items: List[str] = []
    for sec in m.get("subtopics", []):
        sub_items.extend(sec.get("items", []))
    sub_items = [s for s in sub_items if s][:12]
    m["pubmed"] = _build_pubmed_queries(topic, sub_items)
    return m
