# app/rag_retriever.py
import os, pickle
from typing import List, Dict, Any
import faiss, numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR= os.path.join(BASE_DIR, "scripts")
DATA_ROOT  = os.path.join(SCRIPTS_DIR, "data")

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_cache = {}  # {(course): (index, previews, meta)}
_embedder = None

def _course_key(course: str) -> str:
    return (course or "").strip().lower().replace(" ", "_")

def _paths_for(course: str):
    name = _course_key(course)
    root = os.path.join(DATA_ROOT, name)
    return os.path.join(root, "faiss.index"), os.path.join(root, "index.pkl")

def _ensure_loaded(course: str):
    global _embedder, _cache
    ck = _course_key(course)
    if ck in _cache: return
    index_path, meta_path = _paths_for(ck)
    if not (os.path.exists(index_path) and os.path.exists(meta_path)):
        raise FileNotFoundError(f"Vector store not found for '{course}' at {index_path} / {meta_path}")
    index = faiss.read_index(index_path)
    with open(meta_path, "rb") as f:
        data = pickle.load(f)
    previews = data["previews"]; meta = data["metadata"]
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    _cache[ck] = (index, previews, meta)

def retrieve_context(course: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    _ensure_loaded(course)
    index, previews, meta = _cache[_course_key(course)]
    q = _embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
    D, I = index.search(q, top_k)
    out: List[Dict[str, Any]] = []
    for rank, (idx, dist) in enumerate(zip(I[0], D[0]), start=1):
        if 0 <= idx < len(previews):
            m = meta[idx] or {}
            out.append({
                "rank": rank,
                "text": previews[idx],
                "source": {
                    "file": m.get("file", ""),
                    "chapter": m.get("chapter", "Unknown Chapter"),
                    "page": int(m.get("page", 0) or 0),
                },
                "distance": float(dist),
            })
    return out