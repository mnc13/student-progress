from __future__ import annotations

"""
app/services/plan.py

Unified planning module with:
- Groq LLM initialization (tolerant to deprecated models or missing key)
- LLM JSON call helper with fallback
- Fallback task planning when LLM unavailable
- LLM per-topic task planning (4–6 tasks)
- Study task generation + persistence
- Topic enrichment (subtopics + curated resources)
- PubMed helpers (URL builders, MeSH, E-utilities)
- Subtopic-map prompt that yields a stepwise "how to learn" plan
- Convenience wrapper to attach PubMed bundle to the subtopic map
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

# ========== Patch internal Groq httpx wrappers to drop unsupported "proxies" argument ==========
try:
    from groq._base_client import SyncHttpxClientWrapper
    _orig_init = SyncHttpxClientWrapper.__init__
    def _patched_init(self, *args, **kwargs):
        kwargs.pop("proxies", None)
        return _orig_init(self, *args, **kwargs)
    SyncHttpxClientWrapper.__init__ = _patched_init
except Exception:
    # If the internal class layout is different, ignore
    pass

# ========== Groq client initialization ==========

_client = None
def _init_groq_client():
    global _client
    if not settings.HAS_GROQ:
        _client = None
        return
    try:
        from groq import Groq  # local import
        _client = Groq(api_key=settings.GROQ_API_KEY)
        log.info("[LLM] Groq client initialized successfully.")
    except Exception as e:
        log.error("[LLM] Failed to initialize Groq client: %s", e, exc_info=True)
        _client = None

_init_groq_client()

# Use configured model or a safer default
DEFAULT_MODEL = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")

# ========== Prompts ==========

SYSTEM_TASK_PROMPT = (
    "You are a medical education coach for MBBS students. "
    "Create concise, actionable tasks that use evidence-based strategies "
    "(spaced repetition, active recall, case-based learning). "
    "Keep tasks specific and time-bounded. Answer with JSON following schema."
)

SYSTEM_ENRICH_PROMPT = (
    "You are an expert MBBS content curator. For each topic, list high-yield subtopics "
    "and 3–6 relevant study resources (mix of articles/guidelines and YouTube videos). "
    "Only include trustworthy sources; if unsure, omit. Return strict JSON."
)

SYSTEM_SUBTOPIC_MAP = (
    "You are an MBBS academic coach. Extract granular, exam-relevant subtopics and build a concise, "
    "stepwise study map that tells a student exactly what to learn under a topic and how to learn it. "
    "Use evidence-based methods (spaced repetition, active recall, interleaving, case-based learning, error logs). "
    "Return STRICT JSON only, no commentary."
)

def _chat_json(messages: List[Dict[str, Any]], *, max_tokens: int = 2000) -> Optional[Dict[str, Any]]:
    """Call Groq Chat Completions expecting JSON. Return parsed dict or None."""
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
        log.error("ERROR:plan:[LLM] chat failed: %s", e, exc_info=True)
        return None
    import json
    try:
        return json.loads(content)
    except Exception as e:
        log.error("ERROR:plan:[LLM] JSON parse failed: %s", e, exc_info=True)
        return None

# ========== PubMed / URL helpers ==========

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
    return (
        "https://meshb.nlm.nih.gov/search?searchInField=term&sort=pertinence&size=200"
        "&searchType=contains&query=" + quote_plus(term)
    )

def _bookshelf_search_url(query: str) -> str:
    return "https://www.ncbi.nlm.nih.gov/books/?term=" + quote_plus(query)

def _radiopaedia_search_url(query: str) -> str:
    return "https://radiopaedia.org/search?lang=us&q=" + quote_plus(query)

def _build_pubmed_queries(topic: str, subtopics: List[str]) -> Dict[str, Any]:
    topic_q = topic.strip()
    base_q = f"({topic_q})"
    recent_filter = {"filter": "years.5"}

    bundle: Dict[str, Any] = {
        "topic": topic_q,
        "overview": {
            "pubmed_ui": _pubmed_search_url(base_q, filters=recent_filter),
            "pubmed_esearch": _pubmed_esearch_url(base_q),
            "mesh": _mesh_browse_url(topic_q),
            "bookshelf": _bookshelf_search_url(topic_q),
        },
        "angles": {
            "recent_reviews": _pubmed_search_url(
                f"{base_q} AND (review[Publication Type])", filters=recent_filter
            ),
            "guidelines": _pubmed_search_url(
                f"{base_q} AND (guideline[Publication Type] OR practice guideline[Publication Type])",
                filters=recent_filter,
            ),
            "clinical_trials": _pubmed_search_url(
                f"{base_q} AND (randomized controlled trial[Publication Type] OR clinical trial[Publication Type])",
                filters=recent_filter,
            ),
            "imaging": _pubmed_search_url(
                f"{base_q} AND (diagnostic imaging[MeSH Terms] OR radiography OR ultrasound OR MRI OR CT)",
                filters=recent_filter,
            ),
        },
        "by_subtopic": [],
        "adjacent_resources": {
            "radiopaedia": _radiopaedia_search_url(topic_q),
        },
    }

    for st in (subtopics or [])[:10]:
        st_q = st.strip()
        if not st_q:
            continue
        q = f'("{topic_q}") AND ("{st_q}"[Title/Abstract] OR "{st_q}"[MeSH Terms])'
        bundle["by_subtopic"].append(
            {
                "subtopic": st_q,
                "pubmed_ui": _pubmed_search_url(q, filters=recent_filter),
                "pubmed_esearch": _pubmed_esearch_url(q),
                "mesh": _mesh_browse_url(st_q),
            }
        )

    return bundle

# ========== Fallback plan (if LLM fails or is unavailable) ==========

def _fallback_plan(upc: UpcomingEvent, weak_topics: List[str]) -> List[Dict[str, Any]]:
    log.info("[LLM] Using fallback plan for topic=%s (no LLM)", upc.topic)
    due = upc.date
    blocks = [
        {"title": f"Core reading: {upc.topic}", "days_before": 7, "hours": max(1, upc.hours // 5)},
        {"title": f"Active recall (flashcards): {upc.topic}", "days_before": 5, "hours": max(1, upc.hours // 6)},
        {"title": f"Clinical cases & images: {upc.topic}", "days_before": 3, "hours": max(1, upc.hours // 6)},
        {"title": "MCQ practice + review weak areas", "days_before": 2, "hours": max(1, upc.hours // 6)},
        {"title": "Final revision & rest", "days_before": 0, "hours": 1},
    ]
    if weak_topics:
        blocks.insert(
            1,
            {
                "title": f"Remediate weak topic(s): {', '.join(weak_topics[:2])}",
                "days_before": 6,
                "hours": 2,
            },
        )
    return [
        {
            "title": b["title"],
            "due_date": (due - timedelta(days=b["days_before"])).isoformat(),
            "hours": b["hours"],
            "topic": upc.topic,
        }
        for b in blocks
    ]

# ========== LLM per-topic plan ==========

def _llm_topic_plan(upc: UpcomingEvent, weak_topics: List[str]) -> List[Dict[str, Any]]:
    messages = [
        {"role": "system", "content": SYSTEM_TASK_PROMPT},
        {
            "role": "user",
            "content": f"""
Create a short study plan for a single upcoming topic.

Context:
- Course: {upc.course}
- Topic: {upc.topic}
- Event date: {upc.date}
- Available study hours for this topic: ~{upc.hours}
- Historically weak topics in this course: {', '.join(weak_topics) if weak_topics else 'None'}

Requirements:
- Output 4–6 tasks, each with:
  - "title": concise action
  - "topic": "{upc.topic}"
  - "due_date": YYYY-MM-DD between today and {upc.date}
  - "hours": integer between 1 and 3; the sum should be close to {upc.hours}
  - "subtopics": 3–7 bullets
  - "resources": 2–5 items; each is {{ "title": str, "url": str, "kind": "web"|"youtube" }}
- Prefer active recall, images, cases, MCQs.
- STRICT JSON with this schema:
{{  "tasks": [  {{ "title": "str", "topic": "str", "due_date": "YYYY-MM-DD", "hours": 1, "subtopics": ["str", "..."], "resources": [{{"title":"str","url":"str","kind":"web|youtube"}}]  }} ] }}
""".strip(),
        },
    ]
    data = _chat_json(messages)
    if not data or "tasks" not in data or not isinstance(data["tasks"], list):
        return []

    tasks: List[Dict[str, Any]] = []
    for t in data["tasks"]:
        try:
            due_str = str(t["due_date"])
            try:
                dd = date.fromisoformat(due_str)
                if dd > upc.date:
                    due_str = upc.date.isoformat()
            except Exception:
                due_str = upc.date.isoformat()

            hrs = int(t.get("hours", 1))
            hrs = max(1, min(3, hrs))

            tasks.append(
                {
                    "title": str(t["title"])[:200],
                    "topic": upc.topic,
                    "due_date": due_str,
                    "hours": hrs,
                    "subtopics": list(t.get("subtopics", []))[:10],
                    "resources": list(t.get("resources", []))[:6],
                }
            )
        except Exception:
            continue

    return tasks

# ========== Persist tasks to DB ==========

def generate_study_tasks(
    db: Session,
    student_id: int,
    course: str,
    *,
    final_only: bool = False,
    use_llm: bool = True,
) -> List[StudyTask]:
    upcomings = db.scalars(
        select(UpcomingEvent).where(
            UpcomingEvent.student_id == student_id,
            UpcomingEvent.course == course,
        )
    ).all()

    past = db.scalars(
        select(PastItem).where(PastItem.student_id == student_id, PastItem.course == course)
    ).all()
    weak_topics = [p.topic for p in past if (p.mark or 0.0) < 0.5]

    created: List[StudyTask] = []

    if use_llm and _client is None:
        log.error("[LLM] Requested but unavailable (no key)")
        raise RuntimeError("LLM requested but not available")

    for upc in upcomings:
        db.execute(
            delete(StudyTask).where(
                StudyTask.student_id == student_id,
                StudyTask.course == course,
                StudyTask.event_idx == upc.idx,
            )
        )

        tasks_json: List[Dict[str, Any]] = []
        if use_llm:
            tasks_json = _llm_topic_plan(upc, weak_topics)
            if not tasks_json:
                log.warning("[LLM] Returned no tasks for topic=%s; falling back.", upc.topic)

        if not tasks_json:
            tasks_json = _fallback_plan(upc, weak_topics)

        for t in tasks_json:
            try:
                due = date.fromisoformat(str(t["due_date"]))
                hours = int(t.get("hours", 1))
                title = str(t["title"])[:200]
                topic_for_row = (t.get("topic") or upc.topic)[:120]
            except Exception:
                continue

            row = StudyTask(
                student_id=student_id,
                course=upc.course,
                event_idx=upc.idx,
                title=title,
                topic=topic_for_row,
                due_date=due,
                hours=hours,
                status="not_started",
                completion_percent=0,
            )
            db.add(row)
            created.append(row)

    db.commit()
    return created

# ========== Topic enrichment (subtopics + resources + PubMed) ==========

def fetch_topic_enrichment(course: str, topics: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Returns per-topic enrichment including subtopics, curated resources, and PubMed URL bundles.
    If JSON generation fails (e.g. json_validate_failed), fall back gracefully.
    """
    import json
    # fallback deterministic path if LLM unavailable
    if _client is None:
        out: Dict[str, Dict[str, Any]] = {}
        for t in topics:
            subs = [
                f"{t}: core concepts",
                f"{t}: clinical relevance",
                f"{t}: imaging/cadaveric correlation",
                f"{t}: MCQ pitfalls",
            ]
            res = [
                {
                    "title": f"{t} overview (article)",
                    "url": f"https://www.ncbi.nlm.nih.gov/search/all/?term={t.replace(' ', '%20')}",
                    "kind": "article",
                },
                {
                    "title": f"{t} lecture (YouTube)",
                    "url": f"https://www.youtube.com/results?search_query={t.replace(' ', '+')}+mbbs",
                    "kind": "video",
                },
                {
                    "title": f"{t} images/atlas",
                    "url": f"https://radiopaedia.org/search?lang=us&q={t.replace(' ', '%20')}",
                    "kind": "site",
                },
            ]
            out[t] = {"subtopics": subs, "resources": res}
            out[t]["pubmed"] = _build_pubmed_queries(t, subs)
        return out

    user_prompt = {
        "role": "user",
        "content": (
            "You are a medical education assistant for MBBS students.\n"
            f"Course: {course}\n"
            f"Topics: {topics}\n"
            "For EACH topic, produce 4–8 concise subtopics and 4–6 curated resources (title, url, kind: video|article|site). Prefer reputable sources. Output strict JSON.\n"
            '{ "Topic": { "subtopics": ["..."], "resources":[{"title":"...","url":"...","kind":"video|article|site"}] } }'
        ),
    }

    try:
        resp = _client.chat.completions.create(
            model=DEFAULT_MODEL,
            temperature=0.2,
            max_tokens=1200,
            messages=[{"role": "system", "content": "Return JSON only."}, user_prompt],
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        parsed = json.loads(content)
    except Exception as e:
        # If it's a Groq BadRequest / json_validate_failed, fallback
        try:
            import groq
            if isinstance(e, groq.BadRequestError):
                # Try inspect response body
                body = getattr(e, "response", None)
                if body:
                    try:
                        errjson = body.json()
                    except Exception:
                        errjson = {}
                    err = errjson.get("error", {})
                    if err.get("code") == "json_validate_failed":
                        failed = err.get("failed_generation")
                        log.warning("[LLM] enrichment json_validate_failed for topics %s. failed_generation: %s", topics, failed)
                        # fallback path
                        # Build minimal output for each topic
                        fallback: Dict[str, Dict[str, Any]] = {}
                        for t in topics:
                            subs = [
                                f"{t}: core concepts",
                                f"{t}: MCQ pitfalls"
                            ]
                            res = [
                                {
                                    "title": f"{t} search (PubMed)",
                                    "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={t.replace(' ', '%20')}",
                                    "kind": "article",
                                },
                            ]
                            fallback[t] = {"subtopics": subs, "resources": res}
                            fallback[t]["pubmed"] = _build_pubmed_queries(t, subs)
                        return fallback
        except ImportError:
            pass

        log.error("[LLM] enrichment failed unexpectedly for topics %s: %s", topics, e, exc_info=True)
        # fallback deterministic
        out: Dict[str, Dict[str, Any]] = {}
        for t in topics:
            subs = [
                f"{t}: core concepts",
                f"{t}: clinical relevance",
                f"{t}: imaging/cadaveric correlation",
                f"{t}: MCQ pitfalls",
            ]
            res = [
                {
                    "title": f"{t} overview (article)",
                    "url": f"https://www.ncbi.nlm.nih.gov/search/all/?term={t.replace(' ', '%20')}",
                    "kind": "article",
                },
                {
                    "title": f"{t} lecture (YouTube)",
                    "url": f"https://www.youtube.com/results?search_query={t.replace(' ', '+')}+mbbs",
                    "kind": "video",
                },
                {
                    "title": f"{t} images/atlas",
                    "url": f"https://radiopaedia.org/search?lang=us&q={t.replace(' ', '%20')}",
                    "kind": "site",
                },
            ]
            out[t] = {"subtopics": subs, "resources": res}
            out[t]["pubmed"] = _build_pubmed_queries(t, subs)
        return out

    # Normal path: parse successful JSON
    out: Dict[str, Dict[str, Any]] = {}
    for t in topics:
        node = parsed.get(t) if isinstance(parsed, dict) else None
        if not isinstance(node, dict):
            # fallback for that topic
            subs = [f"{t}: core concepts", f"{t}: MCQ pitfalls"]
            res = [
                {
                    "title": f"{t} search (PubMed)",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={t.replace(' ', '%20')}",
                    "kind": "article",
                }
            ]
            out[t] = {"subtopics": subs, "resources": res}
            out[t]["pubmed"] = _build_pubmed_queries(t, subs)
        else:
            subs = [str(s) for s in (node.get("subtopics") or [])][:12]
            clean_res: List[Dict[str, str]] = []
            for r in (node.get("resources") or [])[:10]:
                try:
                    clean_res.append({
                        "title": str(r.get("title", ""))[:200],
                        "url": str(r.get("url", "")),
                        "kind": str(r.get("kind", "site")).lower(),
                    })
                except Exception:
                    continue
            out[t] = {"subtopics": subs, "resources": clean_res}
            out[t]["pubmed"] = _build_pubmed_queries(t, subs)
    return out

# ========== Subtopic map & path ==========

def subtopic_map_user_prompt(topic: str, course: str) -> Dict[str, str]:
    return {
        "role": "user",
        "content": f"""
Course: {course}
Topic: {topic}

Goals:
- List 8–16 granular, MBBS-relevant subtopics (grouped by logical sections).
- Produce a stepwise 'how to learn' map: for each step specify modality, concrete action, deliverable, and time box.
- Include an 'assessment' step (timed MCQs + error log) and an 'images/cases' step.
- Suggest 3–6 trusted resource hints (titles only; no URLs needed here).
- If subtopics imply radiology/surface anatomy/OSCE, include a dedicated step for that.

STRICT JSON SCHEMA:
{{
  "topic": "str",
  "subtopics": [
    {{"section": "str", "items": ["str", "..."]}}
  ],
  "study_path": [
    {{
      "step": 1,
      "title": "str (imperative, <=100 chars)",
      "modality": "Reading|Anki|MCQ|Cases|Diagram|OSCE",
      "action": "str (what exactly to do)",
      "deliverable": "str (e.g., concept map, error log, labeled diagram)",
      "time_box_hours": 1
    }}
  ],
  "resource_hints": ["str", "..."]
}}
"""
    }

def fetch_subtopic_map(topic: str, course: str) -> Optional[Dict[str, Any]]:
    try:
        data = _chat_json([{"role": "system", "content": SYSTEM_SUBTOPIC_MAP},
                           subtopic_map_user_prompt(topic, course)],
                          max_tokens=1400)
    except Exception as e:
        log.error("[LLM] subtopic_map failed for topic %s: %s", topic, e, exc_info=True)
        return None
    if not isinstance(data, dict):
        return None
    # Optionally sanitize fields
    data["topic"] = str(data.get("topic", topic))[:200]
    data["subtopics"] = data.get("subtopics", [])
    data["study_path"] = data.get("study_path", [])
    data["resource_hints"] = data.get("resource_hints", [])
    return data

def fetch_subtopic_map_with_pubmed(topic: str, course: str) -> Optional[Dict[str, Any]]:
    data = fetch_subtopic_map(topic, course)
    if not data:
        return None
    sub_items: List[str] = []
    for sec in data.get("subtopics", []):
        sub_items.extend(sec.get("items", []))
    sub_items = [s for s in sub_items if s][:12]
    data["pubmed"] = _build_pubmed_queries(topic, sub_items)
    return data
