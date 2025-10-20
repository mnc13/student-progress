import os
import re
import pickle
import textwrap
from typing import Iterable, Dict, List

import faiss
import fitz  # PyMuPDF
import numpy as np
from sentence_transformers import SentenceTransformer

# -------------------------------------------------
# Paths
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(BASE_DIR, "anatomy.pdf")   # put PDF next to this script
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

INDEX_FILE = os.path.join(DATA_DIR, "faiss.index")
META_FILE  = os.path.join(DATA_DIR, "index.pkl")

# -------------------------------------------------
# Config (RAM-friendly)
# -------------------------------------------------
EMBED_MODEL      = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE       = 1600    # larger chunk => fewer chunks
CHUNK_OVERLAP    = 0       # zero overlap to minimize count
BATCH_MAX_CHUNKS = 800     # embed this many chunks per batch
PREVIEW_LEN      = 240

chapter_regex = re.compile(r"^\s*Chapter\s+\d+\b.*", re.IGNORECASE)

def chunk_text_stream(txt: str, size: int, overlap: int) -> Iterable[str]:
    """
    Generator (NO big lists). Yields slices of txt.
    """
    if not txt:
        return
    txt = txt.strip()
    n = len(txt)
    start = 0
    if overlap < 0:
        overlap = 0
    while start < n:
        end = start + size
        if end > n:
            end = n
        yield txt[start:end]
        if end == n:
            break
        # next window start
        start = end - overlap
        if start < 0 or start >= n:
            break

def likely_header(line: str) -> bool:
    """
    Treat obvious headings as headers:
      - lines starting with 'Chapter ' or 'Section '
      - ALL-CAPS lines of reasonable length (e.g., 'UPPER LIMB')
      - Short ALL-CAPS with digits (e.g., 'SECTION 1')
    """
    s = (line or "").strip()
    if not s:
        return False
    return (
        s.lower().startswith("chapter ")
        or s.lower().startswith("section ")
        or (s.isupper() and len(s) >= 8)
        or (s.replace(" ", "").isupper() and any(ch.isdigit() for ch in s))
    )

def main():
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF not found at: {PDF_PATH}")

    print("[INFO] Loading PDF...")
    doc = fitz.open(PDF_PATH)

    # -------- First pass: detect chapter/section header per page --------
    chapter_for_page: Dict[int, str] = {}
    last_header = "Unknown Chapter"
    for p in range(len(doc)):
        page_text = doc[p].get_text("text") or ""
        header = None
        for line in page_text.splitlines():
            s = line.strip()
            # accept either strict "Chapter N ..." or broader "likely_header"
            if chapter_regex.match(s) or likely_header(s):
                header = s
                break
        if header:
            last_header = header
        chapter_for_page[p] = last_header

    print("[INFO] Building FAISS index incrementally…")
    embedder = SentenceTransformer(EMBED_MODEL)
    dim = embedder.get_sentence_embedding_dimension()
    index = faiss.IndexFlatL2(dim)

    all_previews: List[str] = []
    all_meta: List[Dict] = []

    batch_texts: List[str] = []
    batch_meta: List[Dict]  = []

    def flush_batch():
        nonlocal batch_texts, batch_meta, index, all_previews, all_meta
        if not batch_texts:
            return
        print(f"[INFO] Embedding batch of {len(batch_texts)} chunks…")
        embs = embedder.encode(
            batch_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)
        index.add(embs)
        # store preview + meta only (keeps meta.pkl small)
        for t, m in zip(batch_texts, batch_meta):
            all_previews.append(t[:PREVIEW_LEN].replace("\n", " "))
            all_meta.append(m)
        batch_texts.clear()
        batch_meta.clear()

    total_chunks = 0
    print("[INFO] Creating chunks with page metadata…")
    for p in range(len(doc)):
        page_text = (doc[p].get_text("text") or "").strip()
        if not page_text:
            continue
        for ch in chunk_text_stream(page_text, CHUNK_SIZE, CHUNK_OVERLAP):
            batch_texts.append(ch)
            batch_meta.append({
                "file": os.path.basename(PDF_PATH),
                "chapter": chapter_for_page.get(p, "Unknown Chapter"),
                "page": p + 1
            })
            total_chunks += 1
            if len(batch_texts) >= BATCH_MAX_CHUNKS:
                flush_batch()

    # final flush
    flush_batch()
    doc.close()

    print(f"[INFO] Total chunks embedded: {total_chunks}")
    faiss.write_index(index, INDEX_FILE)
    with open(META_FILE, "wb") as f:
        pickle.dump({"previews": all_previews, "metadata": all_meta}, f)

    print(f"[SUCCESS] Saved index: {INDEX_FILE}")
    print(f"[SUCCESS] Saved meta : {META_FILE}")

    print("\n========== SAMPLE ENTRIES ==========")
    for i in range(min(5, len(all_previews))):
        meta = all_meta[i]
        label = f"{meta['file']} - {meta['chapter']} (p{meta['page']})"
        print(f"ID: {i} | {label}")
        print(textwrap.fill(all_previews[i], width=100))
        print("-" * 80)

    print(f"\n[INFO] FAISS index built with {index.ntotal} vectors.")
    print("[DONE] Vector store ready.")

if __name__ == "__main__":
    main()
