import os
import pickle
from typing import List, Dict, Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# This file lives in app/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ Your index lives in app/scripts/data
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
DATA_DIR    = os.path.join(SCRIPTS_DIR, "data")
INDEX_PATH  = os.path.join(DATA_DIR, "faiss.index")
META_PATH   = os.path.join(DATA_DIR, "index.pkl")

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_index = None
_previews = None
_meta = None
_embedder = None

def _load():
    global _index, _previews, _meta, _embedder
    if _index is None:
        if not (os.path.exists(INDEX_PATH) and os.path.exists(META_PATH)):
            raise FileNotFoundError(f"Vector store not found at: {INDEX_PATH} and {META_PATH}")
        _index = faiss.read_index(INDEX_PATH)
        with open(META_PATH, "rb") as f:
            data = pickle.load(f)
        _previews = data["previews"]
        _meta     = data["metadata"]
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)

def retrieve_context(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    _load()
    q = _embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
    D, I = _index.search(q, top_k)

    out: List[Dict[str, Any]] = []
    for rank, (idx, dist) in enumerate(zip(I[0], D[0]), start=1):
        if 0 <= idx < len(_previews):
            meta = _meta[idx] or {}
            src = {
                "file": meta.get("file", "anatomy.pdf"),
                "chapter": meta.get("chapter", "Unknown Chapter"),
                "page": int(meta.get("page", 0) or 0),
            }
            out.append({
                "rank": rank,
                "text": _previews[idx],   # short preview
                "source": src,
                "distance": float(dist),
            })
    return out
