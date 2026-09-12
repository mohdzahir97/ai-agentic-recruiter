"""AI endpoints: run an agent on demand.

These are the seams where the AI layer is visible from outside. `/ai/status`
in particular is worth keeping: it says which provider is live and whether the
rule-based fallback is in use, which is the first thing to check when a
screening comes back looking suspiciously mechanical.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents import job_agent, resume_agent
from app.agents.llm import llm_available, model_label
from app.api.deps import require_candidate, require_recruiter
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Candidate, Recruiter
from app.rag import vector_store
from app.rag.embeddings import embedding_label
from app.schemas.ai import AnalyzeTextRequest, JobAnalysis, ResumeAnalysis, ScreeningRequest
from app.schemas.application import ScreeningOut
from app.schemas.candidate import ResumeOut
from app.services import application_service, job_service, resume_service, screening_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status")
def status() -> dict:
    """Which model and embeddings are actually in use right now."""
    settings = get_settings()
    try:
        collections = vector_store.stats()
    except Exception as exc:  # Chroma not initialised yet
        collections = {"error": str(exc)}
    return {
        "llm_available": llm_available(),
        "llm": model_label(),
        "embeddings": embedding_label(),
        "using_fallback": not llm_available(),
        "retrieval_top_k": settings.retrieval_top_k,
        "chunk_size": settings.chunk_size,
        "vector_store": collections,
    }


@router.post("/resume/analyze", response_model=ResumeOut)
def analyze_my_resume(
    candidate: Candidate = Depends(require_candidate), db: Session = Depends(get_db)
) -> ResumeOut:
    """Run the Resume Agent over the candidate's latest resume and store the result."""
    resume = resume_service.analyze(db, candidate)
    return resume_service.to_out(resume)


@router.post("/resume/analyze-text", response_model=ResumeAnalysis)
def analyze_resume_text(
    payload: AnalyzeTextRequest, candidate: Candidate = Depends(require_candidate)
) -> ResumeAnalysis:
    """Try the Resume Agent on arbitrary text, without touching the database."""
    analysis, _ = resume_agent.analyze_resume(payload.text)
    return analysis


@router.post("/job/analyze", response_model=JobAnalysis)
def analyze_job_text(
    payload: AnalyzeTextRequest, recruiter: Recruiter = Depends(require_recruiter)
) -> JobAnalysis:
    """Try the Job Agent on a description before committing to a posting."""
    analysis, _ = job_agent.analyze_job(
        title="", company="", description=payload.text, required_skills=[], preferred_skills=[]
    )
    return analysis


@router.post("/job/{job_id}/analyze", response_model=JobAnalysis)
def reanalyze_job(
    job_id: int,
    recruiter: Recruiter = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> JobAnalysis:
    """Re-run the Job Agent on a saved job and store the fresh analysis."""
    job = job_service.owned_job(db, recruiter, job_id)
    job = job_service.run_job_agent(db, job)
    return JobAnalysis.model_validate(job.jd_analysis or {})


@router.post("/screen/{application_id}", response_model=ScreeningOut, status_code=201)
def screen_application(
    application_id: int,
    payload: ScreeningRequest | None = None,
    recruiter: Recruiter = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> ScreeningOut:
    """Run the full screening workflow: plan, analyse, retrieve, compare, evaluate.

    Produces a recommendation for a human. It moves the application to
    SCREENING and stops there — the decision is `POST /applications/{id}/review`.
    """
    application = application_service.get_for_recruiter(db, recruiter, application_id)
    screening = screening_service.screen(db, application, force=bool(payload and payload.force))
    return application_service.screening_out(screening)
