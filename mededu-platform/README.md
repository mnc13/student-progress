# MedEdu Platform (Next.js + Express + FastAPI + Postgres)

Monorepo with:
- `apps/web`: Next.js + Tailwind frontend
- `services/api`: Express (TypeScript) API + Prisma
- `services/ml`: FastAPI microservice for google/medgemma-4b-it
- `infra`: Docker Compose / Dockerfiles

## Quick start (local, no Docker)
1) Start your Postgres DB (you said it's already created) and set `services/api/.env`.
2) API
```bash
cd services/api
pnpm i
pnpx prisma db pull
pnpx prisma generate
pnpm dev
```
3) ML service (Python)
```bash
cd services/ml
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows (Powershell): .venv\Scripts\Activate.ps1
pip install -r requirements.txt
export MODEL_ID=google/medgemma-4b-it
uvicorn app.main:app --reload --port 8000
```
4) Web
```bash
cd apps/web
pnpm i
pnpm dev
```
Open http://localhost:3000/study
