# app/routers/content.py
from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any
from app.services.plan import fetch_topic_enrichment, fetch_subtopic_map_with_pubmed

router = APIRouter(prefix="/courses", tags=["content"])


@router.get("/{course}/topics/{topic}/syllabus")
def get_syllabus(course: str, topic: str) -> Dict[str, Any]:
    """
    Returns subtopics + curated links + PubMed bundle for a single topic.
    """
    data = fetch_topic_enrichment(course, [topic])
    node = data.get(topic)
    if node is None:
        # fallback: try subtopic + pubmed map directly
        node2 = fetch_subtopic_map_with_pubmed(topic, course)
        if node2:
            return {
                "subtopics": node2.get("subtopics", []),
                "resources": node2.get("resources", []),
                "pubmed": node2.get("pubmed"),
            }
        # fallback empty
        return {"subtopics": [], "resources": [], "pubmed": None}
    return node


@router.post("/{course}/topics/syllabus/batch")
def syllabus_batch(
    course: str,
    topics: List[str] = Body(..., embed=True, description="List of topics"),
) -> Dict[str, Any]:
    """
    Batch endpoint: returns syllabus info (subtopics, resources, pubmed) for each topic.
    """
    data = fetch_topic_enrichment(course, topics)
    out: Dict[str, Any] = {}
    for t in topics:
        node = data.get(t)
        if node is None:
            node2 = fetch_subtopic_map_with_pubmed(t, course)
            if node2:
                out[t] = {
                    "subtopics": node2.get("subtopics", []),
                    "resources": node2.get("resources", []),
                    "pubmed": node2.get("pubmed"),
                }
            else:
                out[t] = {"subtopics": [], "resources": [], "pubmed": None}
        else:
            out[t] = node
    return out
