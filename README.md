# AI Recruitment MVP — Phase 1

A small, complete recruitment workflow built to demonstrate six things working
together end to end:

**GenAI agents · RAG · agent orchestration · semantic matching · AI explainability · human-in-the-loop**

Two roles, one workflow: a candidate uploads a resume and applies; a recruiter
posts a job and asks the AI to screen the applicant; the AI produces a scored,
evidence-backed recommendation; **a human makes the decision.**

---

## What it does

```
 CANDIDATE                                    RECRUITER
     │                                            │
 upload resume (PDF)                         create job
     │                                            │
 text extraction                             Job Agent
     │                                            │
 Resume Agent ──► structured profile          structured requirements
     │                                            │
     └──────────────┬─────────────────────────────┘
                    ▼
              apply to job
                    │
                    ▼
            ┌───────────────┐
            │  AI SCREENING │   LangGraph: goal → plan → execute → evaluate
            └───────┬───────┘
                    │
         retrieve context (RAG over ChromaDB)
                    │
         compare · score · explain
                    │
                    ▼
       match % · confidence % · strengths · gaps · evidence
                    │
                    ▼
            👤 RECRUITER REVIEW          ◄── the AI stops here
                    │
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
  SHORTLIST       HOLD         REJECT
```

The AI never sets a final status. `POST /applications/{id}/review` is the only
endpoint that can, and it requires an authenticated recruiter.

---

## Quick start

### Option A — everything in Docker

```bash
cp backend/.env.example backend/.env     # add an LLM key, or leave it blank
docker compose up --build
```

- Frontend → http://localhost:3000
- API docs → http://localhost:8000/docs

Then load the demo data:

```bash
docker compose exec backend python seed.py
```

### Option B — run it locally

**Backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate           # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# For zero setup, set DATABASE_URL=sqlite:///./data/app.db in .env

python seed.py --reset           # optional demo data
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

On Windows, `start_all.bat` does both in two terminals.

### Demo accounts

`seed.py` creates these — password **`Passw0rd!23`** for all of them:

| Role | Email |
|---|---|
| Recruiter | `riya.recruiter@example.com` |
| Candidate | `john.doe@example.com` (strong backend match) |
| Candidate | `priya.sharma@example.com` (ML/RAG) |
| Candidate | `arjun.mehta@example.com` (frontend) |

Each candidate has a real resume PDF and has applied to two jobs — including
one they clearly do not fit, so you can see a weak match as well as a strong one.

Nothing is screened yet on purpose. Sign in as the recruiter, open **AI
Screening**, and run one.

---

## It runs with no API key

Set `LLM_PROVIDER=fallback` (or just leave every key blank) and the application
still works end to end. Deterministic keyword-based agents take over, and every
result they produce is labelled `rule-based-fallback` in the API and in the UI.

The same path catches a failed live call — a rate limit or a timeout degrades
the screening instead of breaking it.

Embeddings default to `local`: the MiniLM model bundled with ChromaDB. No key,
no network call, so the RAG pipeline works out of the box too.

Check what is actually live at any time:

```bash
curl http://localhost:8000/api/v1/ai/status
```

```json
{
  "llm_available": true,
  "llm": "groq:openai/gpt-oss-120b",
  "embeddings": "local:all-MiniLM-L6-v2",
  "using_fallback": false,
  "vector_store": { "candidate_docs": 12, "job_docs": 3 }
}
```

The sidebar shows this too, so you always know whether you are looking at model
output or keyword matching.

---

## Verify it

`smoke_test.py` walks every Phase 1 success criterion against a running server —
register both roles, build a profile, upload and analyse a resume, post a job,
apply, screen, and record a human decision:

```bash
cd backend
python smoke_test.py
```

```
PASS  Candidate can register/login  (201)
PASS  RBAC blocks a candidate from recruiter routes  (403)
PASS  AI can extract resume information  (skills=[...] years=6.0 model=groq:openai/gpt-oss-120b)
PASS  RAG retrieves relevant candidate/JD context  (5 chunks)
PASS  AI can calculate a match score  (overall=88.0% skills=100.0% ... conf=90.0%)
PASS  Agent workflow is traced  (plan -> analyze_job -> retrieve_context -> ... -> evaluate)
PASS  Screening moves the application to SCREENING, not a final status
PASS  A rejection without a reason is refused  (422)
PASS  The human decision is stored with the AI's recommendation
...
32/32 checks passed
```

It passes on both the live-LLM and the no-key path.

---

## Configuration

Everything lives in `backend/.env` — see `.env.example` for the annotated list.
The settings you are most likely to change:

| Setting | Default | Notes |
|---|---|---|
| `DATABASE_URL` | PostgreSQL | `sqlite:///./data/app.db` needs nothing installed |
| `LLM_PROVIDER` | `groq` | `groq` · `openai` · `gemini` · `ollama` · `fallback` |
| `LLM_MODEL` | `openai/gpt-oss-120b` | Model for the chosen provider |
| `EMBEDDING_PROVIDER` | `local` | `local` needs no key; `openai`/`gemini`/`ollama` to compare |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 800 / 120 | Change these and watch retrieval quality move |
| `RETRIEVAL_TOP_K` | 4 | Chunks fed to the matching agent |

---

## API

All routes are under `/api/v1`. Full interactive docs at `/docs`.

**Auth** — `POST /auth/register` · `POST /auth/login` · `GET /auth/me`

**Candidate** — `GET|PUT /candidates/me` · `GET /candidates/me/metrics` ·
`POST|GET /candidates/resume` · `GET /candidates/resume/file` ·
`GET /candidates/recommended-jobs` · `GET /candidates/applications`

**Jobs** — `GET|POST /jobs` · `GET|PUT /jobs/{id}` · `POST /jobs/{id}/apply` ·
`GET /jobs/{id}/applications`

**Recruiter** — `GET /recruiter/metrics` · `/recruiter/jobs` ·
`/recruiter/applications` · `/recruiter/screening-queue` · `/recruiter/candidates` ·
`GET /candidates/{id}`

**AI** — `GET /ai/status` · `POST /ai/resume/analyze` · `POST /ai/job/analyze` ·
`POST /ai/screen/{applicationId}`

**HITL** — `POST /applications/{id}/review` · `GET /applications/{id}/candidate-360`

---

## Project layout

```
ai-recruitment-mvp/
├── backend/
│   ├── app/
│   │   ├── agents/          resume_agent · job_agent · matching_agent
│   │   │   ├── graph.py     LangGraph orchestration
│   │   │   ├── llm.py       provider factory + structured output
│   │   │   ├── prompts.py   all prompt text, in one file
│   │   │   ├── safety.py    fairness rules and the output scan
│   │   │   └── fallback.py  deterministic no-LLM agents
│   │   ├── rag/             pdf_loader · chunker · embeddings · vector_store · retriever
│   │   ├── api/v1/          the HTTP layer
│   │   ├── services/        business logic (no FastAPI imports)
│   │   ├── repositories/    the only layer that writes SQL
│   │   ├── models/          SQLAlchemy tables
│   │   ├── schemas/         Pydantic request/response models
│   │   └── core/            config · security · logging · exceptions
│   ├── seed.py              demo data
│   └── smoke_test.py        end-to-end success-criteria check
└── frontend/
    └── src/
        ├── app/             Next.js App Router pages
        ├── components/      ui.tsx · ai.tsx · Shell · JobForm
        └── lib/             api client · auth context · formatting
```

`ARCHITECTURE.md` explains why it is arranged this way, and how the AI layer
actually works.

---

## Phase 1 scope

**In:** two roles with RBAC · candidate profile and resume · AI resume analysis ·
job posting with AI JD analysis · applications · RAG retrieval · AI match scoring
with explanations and evidence · agent orchestration · human-in-the-loop
decisions · application status tracking.

**Deliberately out:** hiring managers, HR/admin, payroll, onboarding, background
checks, notifications, AI interviews, offer management, analytics, and any
autonomous multi-agent behaviour.

**Known limits, stated plainly:**

- No OCR — a scanned, image-only resume is rejected with a clear message rather
  than silently producing an empty analysis.
- `create_all` instead of migrations. Fine for Phase 1; a schema change in
  production would need Alembic.
- The JWT is held in `localStorage`. Simple and stateless, but a production
  build should use httpOnly cookies.
- Screening is synchronous. One LLM call takes a few seconds; a real queue would
  want a background worker.
- The fairness guard is pattern-based. It catches the obvious cases and is one
  layer, not a guarantee.
