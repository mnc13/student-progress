# app/scripts/build_vector_store.py
import os, re, pickle, textwrap, argparse
from typing import Iterable, Dict, List
import faiss, fitz, numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_ROOT, exist_ok=True)

EMBED_MODEL   = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", "1600"))
_overlap_env  = os.getenv("CHUNK_OVERLAP", "0")
if _overlap_env.endswith("%"):
    pct = max(0, min(90, int(_overlap_env[:-1] or "0")))
    CHUNK_OVERLAP = max(0, (CHUNK_SIZE * pct) // 100)
else:
    CHUNK_OVERLAP = max(0, int(_overlap_env))
CROSS_PAGE_OVERLAP = os.getenv("CROSS_PAGE_OVERLAP", "0") not in {"0", "false", "False"}
BATCH_MAX_CHUNKS   = int(os.getenv("BATCH_MAX_CHUNKS", "800"))
PREVIEW_LEN        = int(os.getenv("PREVIEW_LEN", "240"))

chapter_regex = re.compile(r"^\s*Chapter\s+\d+\b.*", re.IGNORECASE)

def chunk_text_stream(txt: str, size: int, overlap: int):
    if not txt or size <= 0: return
    txt = txt.strip(); n = len(txt)
    overlap = max(0, min(overlap, size - 1)); step = size - overlap
    start = 0
    while start < n:
        end = min(start + size, n)
        yield txt[start:end]
        if end >= n: break
        start += step

def likely_header(line: str) -> bool:
    s = (line or "").strip()
    return bool(
        s and (
            s.lower().startswith("chapter ")
            or s.lower().startswith("section ")
            or (s.isupper() and len(s) >= 8)
            or (s.replace(" ", "").isupper() and any(ch.isdigit() for ch in s))
        )
    )

def build(pdf_path: str, out_dir: str):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    os.makedirs(out_dir, exist_ok=True)
    index_file = os.path.join(out_dir, "faiss.index")
    meta_file  = os.path.join(out_dir, "index.pkl")

    print(f"[INFO] Loading: {pdf_path}")
    doc = fitz.open(pdf_path)

    chapter_for_page: Dict[int, str] = {}
    last_header = "Unknown Chapter"
    for p in range(len(doc)):
        page_text = doc[p].get_text("text") or ""
        header = None
        for line in page_text.splitlines():
            s = line.strip()
            if chapter_regex.match(s) or likely_header(s):
                header = s; break
        if header: last_header = header
        chapter_for_page[p] = last_header

    embedder = SentenceTransformer(EMBED_MODEL)
    dim = embedder.get_sentence_embedding_dimension()
    index = faiss.IndexFlatL2(dim)

    all_previews: List[str] = []
    all_meta: List[Dict] = []
    batch_texts: List[str] = []
    batch_meta: List[Dict]  = []

    def flush_batch():
        nonlocal batch_texts, batch_meta
        if not batch_texts: return
        print(f"[INFO] Embedding batch of {len(batch_texts)} chunks…")
        embs = embedder.encode(
            batch_texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
        ).astype(np.float32)
        index.add(embs)
        for t, m in zip(batch_texts, batch_meta):
            all_previews.append(t[:PREVIEW_LEN].replace("\n", " "))
            all_meta.append(m)
        batch_texts.clear(); batch_meta.clear()

    total_chunks = 0
    carry = ""
    print("[INFO] Chunking…")
    for p in range(len(doc)):
        page_text = (doc[p].get_text("text") or "").strip()
        if not page_text:
            carry = "" if CROSS_PAGE_OVERLAP else carry
            continue

        working = (carry + page_text) if (CROSS_PAGE_OVERLAP and carry) else page_text
        for ch in chunk_text_stream(working, CHUNK_SIZE, CHUNK_OVERLAP):
            payload = ch[len(carry):] if (CROSS_PAGE_OVERLAP and carry and ch.startswith(carry) and len(ch) > len(carry)) else ch
            if not payload.strip(): continue

            batch_texts.append(payload)
            batch_meta.append({
                "file": os.path.basename(pdf_path),
                "chapter": chapter_for_page.get(p, "Unknown Chapter"),
                "page": p + 1
            })
            total_chunks += 1
            if len(batch_texts) >= BATCH_MAX_CHUNKS:
                flush_batch()

        carry = page_text[-CHUNK_OVERLAP:] if (CROSS_PAGE_OVERLAP and CHUNK_OVERLAP > 0) else ""

    flush_batch()
    doc.close()

    faiss.write_index(index, index_file)
    with open(meta_file, "wb") as f:
        pickle.dump({"previews": all_previews, "metadata": all_meta}, f)

    print(f"[OK] Chunks: {total_chunks}")
    print(f"[OK] Saved index => {index_file}")
    print(f"[OK] Saved meta  => {meta_file}")
    print("\n========== SAMPLE ==========")
    for i in range(min(5, len(all_previews))):
        meta = all_meta[i]
        label = f"{meta['file']} - {meta['chapter']} (p{meta['page']})"
        print(f"ID: {i} | {label}")
        print(textwrap.fill(all_previews[i], width=100))
        print("-" * 80)
    print(f"[INFO] FAISS vectors: {index.ntotal}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, help="Path to the course PDF")
    ap.add_argument("--out", required=True, help="Output directory (e.g., app/scripts/data/anatomy)")
    args = ap.parse_args()
    build(args.pdf, args.out)
