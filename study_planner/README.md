# MBBS Study Planner (FastAPI + Groq)

A reference backend + tiny frontend that:
- Logs in by `studentID`
- Shows courses and past marks
- Puts upcoming items on a calendar
- Generates a **personalized study plan** (for medical students) using Groq (LLM), based on a student's history
- Tracks completion status and computes % completion for each upcoming item

## Quickstart

1) Python 3.10+ recommended. Create venv and install deps:

```bash
cd app
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
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
2) Set your Groq API key:

```bash
export GROQ_API_KEY=xxxxxxxxxxxxxxxx
# Windows PowerShell
# $Env:GROQ_API_KEY="xxxxxxxxxxxxxxxx"
```

3) Run the server:

```bash
uvicorn main:app --reload
```

4) Open the frontend (static HTML) in your browser:
- Serve `frontend/` via any static server (e.g., VSCode Live Server),
- OR use Python: `python -m http.server 8080 -d frontend` then open http://localhost:8080

5) In the UI, enter a **studentID** (from the CSV, e.g., 500001) and explore.

## Notes

- Database: SQLite file `app.db` created on first run.
- CSV is preloaded from `data/mbbs_personalization.csv` into tables:
  - `students` (student_id)
  - `past_items` (item1..item5 with topic, hours, mark 0..1)
  - `upcoming_events` (upc_item6..10 with topic, hours, date)
  - `study_tasks` (generated per upcoming event; track completion + %)

- Study plan generation uses a Groq model (default: `llama-3.1-70b-versatile`).
  If `GROQ_API_KEY` is missing, a deterministic fallback generator is used.

- Timezone: All dates in the CSV are ISO; frontend calendar renders them as-is.
