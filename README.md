# Personalized Study Planner

Personalized Study Planner is a web application that tracks students' study progress based on past performance and suggests personalized study plans aligned with upcoming exams. The system generates a detailed syllabus with estimated study hours, recommends tailored modules, and links directly to recommended resources. It leverages LLMs (Gemini and Llama) to generate plans and implements Retrieval-Augmented Generation (RAG) with a vector store so students can study relevant topics from source materials (books, notes, etc.) efficiently.

Table of contents
- About
- Key features
- Architecture & components
- Requirements
- Backend setup
- Frontend setup
- Environment variables & secrets
- How it works (brief)
- Useful links
- Troubleshooting

About
-------
This project is intended to help students prepare for exams more effectively by:
- Analyzing historical performance and past study data.
- Creating exam-aligned, date-based study plans with granular syllabus breakdown and estimated study hours.
- Suggesting resources (with direct links) accessible from the app.
- Using LLMs (Gemini and Llama) to generate study plans and employing RAG to retrieve and present contextually relevant content from indexed documents.

Key features
------------
- Personalized study plans that adapt to past performance and upcoming exam dates.
- Detailed syllabus breakdown with estimated study hours per topic.
- Resource recommendations with direct links in the UI.
- Combined LLM approach: Gemini and Llama support (selectable/versatile generation).
- Retrieval-Augmented Generation (RAG) for accurate, source-grounded answers and study material retrieval.
- Vector store building script to create embeddings from provided study resources.

Architecture & components
-------------------------
- Backend: Python FastAPI (serves the API, LLM orchestration, RAG retrieval)
  - app/ - FastAPI app
  - scripts/ - helper scripts (e.g., build vector store)
- Frontend: JavaScript/TypeScript app (Vite / React and Tailwind CSS) under my-app/
- Vector store: built via a script to index PDFs/text and used by RAG
- LLM integrations: Gemini (Google Generative AI) and Llama (local or hosted) — configurable via environment variables

Requirements
------------
- Python 3.10+ (or compatible)
- Node.js + npm
- Windows (PowerShell) commands are shown below; macOS/Linux equivalents are noted where applicable.
- API keys for the generative models (Gemini or Llama host/keys) and any other providers you configure.

Backend setup
-------------
1. Open a terminal and change into the project folder (example path used in these instructions is `study_planner` — adjust if your folder is named `study_planer`):
   - cd study_planner

2. Create and activate a Python virtual environment:
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\activate
     ```
   - macOS / Linux
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Build the vector store (this indexes local resources so RAG can work). From the scripts folder under the app folder:
   - Windows (PowerShell)
     ```
     cd app\scripts
     python .\build_vector_store.py
     ```
   - macOS / Linux
     ```
     cd app/scripts
     python3 ./build_vector_store.py
     ```

4. Install dependencies and required packages. From the project root (`study_planner`):
   ```
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   pip install google-generativeai
   pip install pymupdf
   pip install sentence-transformers
   ```
   (You may combine some of these if desired. On macOS/Linux, you may use `pip3`.)

5. Set required environment variables. Example (PowerShell):
   ```
   $Env:GROQ_API_KEY=""
   ```
   OR
   ```
   $Env:GEMINI_API_KEY=""
   ```
   On macOS / Linux (bash/zsh) you can export:
   ```
   export GROQ_API_KEY=""
   # or
   export GEMINI_API_KEY=""
   ```

   Notes:
   - Use the appropriate key depending on whether you're using Gemini or a provider that requires a GROQ API key.
   - If you are using Llama via a hosted service or custom endpoint, set the corresponding env variables as required by your deployment/config (check app config files or README sections for extra variables).

6. Run the backend (development mode):
   ```
   uvicorn app.main:app --reload
   ```
   By default the backend serves OpenAPI docs at:
   - http://127.0.0.1:8000/docs

Frontend setup
--------------
1. From the project root (`study_planner`), install frontend dependencies:
   ```
   npm install
   ```

2. Start the frontend dev server. From the `my-app` folder:
   ```
   cd my-app
   npm run dev
   ```
   - Default Vite dev server usually runs at: http://localhost:5173 (or a port printed by the command)

Environment variables & secrets
-------------------------------
- GEMINI_API_KEY — (if using Gemini / Google Generative API)
- GROQ_API_KEY — (if using GROQ or another model provider)
- Other provider keys (Llama hosting, vector DB credentials, etc.) — check app configuration files for the exact variable names.
- Never commit API keys or secrets into version control. Use a .env file (added to .gitignore), environment variables on your host, or a secrets manager.

How it works (brief)
--------------------
1. Student data (past performance, exams, resources) is stored/ingested into the backend.
2. The vector store is built from resources (PDFs, notes), generating embeddings via sentence-transformers so RAG can retrieve relevant passages.
3. When a student requests a study plan:
   - The system analyzes past performance and upcoming exam dates.
   - A chosen LLM (Gemini or Llama) is prompted to generate a personalized plan.
   - RAG augments the LLM with context from the vector store so recommendations are grounded in source materials.
4. The generated plan includes dates, detailed syllabi, estimated hours, and direct resource links.

Useful links
------------
- Backend API docs (OpenAPI): http://127.0.0.1:8000/docs
- Frontend (dev server): typically http://localhost:5173

Troubleshooting
---------------
- If build_vector_store.py errors: ensure required files (PDFs, text resources) are present where the script expects them and that dependencies (pymupdf, sentence-transformers) are installed.
- If LLM API calls fail: verify API keys, network connectivity, and any provider-specific configuration.
- If the frontend cannot reach the backend: check CORS settings, backend host/port, and that the backend is running.

