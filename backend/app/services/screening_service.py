"""AI screening: run the agent graph and persist the result.

This service is the bridge between the database and the agent layer. It
gathers the inputs, runs the LangGraph workflow, and writes an `AIScreening`
row. It moves the application to SCREENING — and no further. A terminal
status is a human's to set (see `hitl_service`).
"""
import logging
from typing import Dict, List

from sqlalchemy.orm import Session

from app.agents.graph import run_screening
from app.core.exceptions import AIError, ValidationError
from app.models import AIScreening, Application, ApplicationStatus
from app.rag import retriever
from app.repositories import resume_repo
from app.schemas.ai import MatchResult

logger = logging.getLogger(__name__)

# How much of each retrieved chunk to keep on the screening row. Enough for a
# recruiter to see what the AI was looking at, without storing the resume twice.
CONTEXT_SNIPPET_CHARS = 600


def screen(db: Session, application: Application, force: bool = False) -> AIScreening:
    """Run the screening workflow for one application."""
    if application.latest_screening and not force:
        return application.latest_screening

    candidate = application.candidate
    job = application.job
    resume = resume_repo.latest_for_candidate(db, candidate.id)
    if not resume or not resume.extracted_text:
        raise ValidationError("This candidate has no readable resume to screen")

    # Make sure both sides are indexed before retrieval runs — a job created
    # before the vector store existed would otherwise retrieve nothing.
    _ensure_indexed(db, candidate, job, resume.extracted_text)

    state = run_screening(
        {
            "goal": f"Screen {candidate.user.full_name} for the {job.title} role at {job.company}",
            "candidate_id": candidate.id,
            "job_id": job.id,
            "resume_text": resume.extracted_text,
            "profile_text": retriever.candidate_profile_text(candidate, candidate.user),
            "job_payload": {
                "title": job.title,
                "company": job.company,
                "description": job.description,
                "location": job.location,
                "employment_type": job.employment_type,
                "experience_required": job.experience_required,
                "required_skills": job.required_skills or [],
                "preferred_skills": job.preferred_skills or [],
            },
            "stored_resume_analysis": resume.ai_analysis,
            "stored_job_analysis": job.jd_analysis,
        }
    )

    result: MatchResult = state.get("match")
    if result is None:
        raise AIError("The screening agent produced no result")

    screening = AIScreening(
        application_id=application.id,
        skills_match=result.skills_match,
        experience_match=result.experience_match,
        technology_match=result.technology_match,
        education_match=result.education_match,
        semantic_match=result.semantic_match,
        overall_match=result.overall_match,
        confidence=result.confidence,
        recommendation=result.recommendation.value,
        strengths=result.strengths,
        skill_gaps=result.skill_gaps,
        explanation=result.explanation,
        evidence=[item.model_dump(mode="json") for item in result.evidence],
        retrieved_context=_snippets(state.get("candidate_chunks"), state.get("job_chunks")),
        agent_trace=state.get("trace") or [],
        model_used=state.get("model_used") or "",
        safety_notes=state.get("safety_notes") or [],
    )
    db.add(screening)

    # APPLIED -> SCREENING. Anything further is a human decision, so a
    # re-screen of an already-decided application leaves its status alone.
    if application.status == ApplicationStatus.APPLIED.value:
        application.status = ApplicationStatus.SCREENING.value

    db.commit()
    db.refresh(screening)
    logger.info(
        "Screened application %s: %.1f%% (%s) at %.1f%% confidence via %s",
        application.id,
        screening.overall_match,
        screening.recommendation,
        screening.confidence,
        screening.model_used,
    )
    return screening


def _ensure_indexed(db: Session, candidate, job, resume_text: str) -> None:
    try:
        retriever.index_candidate(candidate, candidate.user, resume_text)
        retriever.index_job(job)
    except Exception as exc:
        # Retrieval will return nothing, the agent will cap its confidence and
        # say so — degraded, but still a usable answer for the recruiter.
        logger.error("Indexing before screening failed: %s", exc)


def _snippets(candidate_chunks: List[Dict], job_chunks: List[Dict]) -> List[Dict]:
    out = []
    for chunk in (candidate_chunks or []) + (job_chunks or []):
        out.append(
            {
                "source": chunk.get("source", "document"),
                "score": chunk.get("score", 0.0),
                "text": (chunk.get("text") or "")[:CONTEXT_SNIPPET_CHARS],
            }
        )
    return out
