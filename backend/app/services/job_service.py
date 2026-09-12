"""Job creation, editing and listing.

Creating or editing a job runs the Job Agent and re-indexes the job for RAG,
so the structured analysis and the vector store are always in step with the
posting a candidate can see.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.agents import job_agent
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models import Candidate, Job, Recruiter
from app.rag import retriever
from app.repositories import application_repo, job_repo
from app.schemas.job import JobCreate, JobOut, JobUpdate, RecommendedJob

logger = logging.getLogger(__name__)


def create(db: Session, recruiter: Recruiter, payload: JobCreate) -> Job:
    job = Job(recruiter_id=recruiter.id, **payload.model_dump())
    job_repo.add(db, job)
    db.commit()
    db.refresh(job)
    run_job_agent(db, job)
    return job


def update(db: Session, recruiter: Recruiter, job_id: int, payload: JobUpdate) -> Job:
    job = _owned(db, recruiter, job_id)
    data = payload.model_dump(exclude_unset=True, mode="json")
    for field, value in data.items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)

    # Only re-run the agent when something it reads actually changed. Editing
    # the location should not spend an LLM call.
    if {"description", "title", "required_skills", "preferred_skills", "experience_required"} & set(data):
        run_job_agent(db, job)
    else:
        _index(job)
    return job


def run_job_agent(db: Session, job: Job) -> Job:
    """Analyse the description, store the result, re-index. Never fatal."""
    try:
        analysis, model = job_agent.analyze_job(
            title=job.title,
            company=job.company,
            description=job.description,
            location=job.location or "",
            employment_type=job.employment_type or "",
            experience_required=job.experience_required,
            required_skills=job.required_skills or [],
            preferred_skills=job.preferred_skills or [],
        )
        job.jd_analysis = analysis.model_dump(mode="json")
        job.analysis_model = model
        job.analyzed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
    except Exception as exc:
        logger.error("Job agent failed for job %s: %s", job.id, exc)
        db.rollback()
    _index(job)
    return job


def _index(job: Job) -> None:
    try:
        retriever.index_job(job)
    except Exception as exc:
        logger.error("Failed to index job %s: %s", job.id, exc)


def get(db: Session, job_id: int) -> Job:
    job = job_repo.get(db, job_id)
    if not job:
        raise NotFoundError("Job not found")
    return job


def _owned(db: Session, recruiter: Recruiter, job_id: int) -> Job:
    job = get(db, job_id)
    if job.recruiter_id != recruiter.id:
        raise ForbiddenError("This job belongs to another recruiter")
    return job


def owned_job(db: Session, recruiter: Recruiter, job_id: int) -> Job:
    return _owned(db, recruiter, job_id)


def list_open(db: Session, candidate: Optional[Candidate], search: str = "") -> List[JobOut]:
    jobs = job_repo.list_active(db, search)
    counts = job_repo.application_counts(db, [job.id for job in jobs])
    applied = application_repo.applied_job_ids(db, candidate.id) if candidate else set()
    return [_to_out(job, counts.get(job.id, 0), job.id in applied) for job in jobs]


def list_for_recruiter(db: Session, recruiter: Recruiter) -> List[JobOut]:
    jobs = job_repo.list_for_recruiter(db, recruiter.id)
    counts = job_repo.application_counts(db, [job.id for job in jobs])
    return [_to_out(job, counts.get(job.id, 0)) for job in jobs]


def to_out(db: Session, job: Job, candidate: Optional[Candidate] = None) -> JobOut:
    counts = job_repo.application_counts(db, [job.id])
    applied = bool(
        candidate and application_repo.get_by_job_and_candidate(db, job.id, candidate.id)
    )
    return _to_out(job, counts.get(job.id, 0), applied)


def recommend(db: Session, candidate: Candidate, limit: int = 6) -> List[RecommendedJob]:
    """Semantic job search using the candidate's own profile as the query.

    The same RAG index that powers screening, read from the other direction.
    """
    query = retriever.candidate_profile_text(candidate, candidate.user)
    resume = candidate.current_resume
    if resume and resume.extracted_text:
        query = f"{query}\n{resume.extracted_text[:2000]}"

    try:
        hits = retriever.recommend_jobs(query, top_k=limit * 3)
    except Exception as exc:
        logger.error("Job recommendation failed for candidate %s: %s", candidate.id, exc)
        hits = []

    if not hits:
        # No index yet (or an empty profile): fall back to the newest openings
        # rather than showing the candidate an empty dashboard.
        return [
            RecommendedJob(**_to_out(job, 0, False).model_dump(), relevance=0.0,
                           reason="Recently posted")
            for job in job_repo.list_active(db)[:limit]
        ]

    jobs = {job.id: job for job in job_repo.list_by_ids(db, [h["metadata"]["job_id"] for h in hits])}
    applied = application_repo.applied_job_ids(db, candidate.id)
    counts = job_repo.application_counts(db, list(jobs))

    recommendations: List[RecommendedJob] = []
    for hit in hits:
        job = jobs.get(hit["metadata"].get("job_id"))
        if not job or job.status != "ACTIVE":
            continue
        base = _to_out(job, counts.get(job.id, 0), job.id in applied)
        recommendations.append(
            RecommendedJob(
                **base.model_dump(),
                relevance=round(hit["score"] * 100, 1),
                reason=_reason(job, candidate),
            )
        )
        if len(recommendations) >= limit:
            break
    return recommendations


def _reason(job: Job, candidate: Candidate) -> str:
    """A short, checkable reason — the overlapping skills, named."""
    have = {skill.lower() for skill in candidate.skills or []}
    overlap = [skill for skill in (job.required_skills or []) if skill.lower() in have]
    if overlap:
        return "Matches your " + ", ".join(overlap[:3])
    return "Semantically similar to your profile"


def _to_out(job: Job, application_count: int, already_applied: bool = False) -> JobOut:
    return JobOut(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        employment_type=job.employment_type,
        experience_required=job.experience_required,
        required_skills=job.required_skills or [],
        preferred_skills=job.preferred_skills or [],
        description=job.description,
        status=job.status,
        created_at=job.created_at,
        jd_analysis=job.jd_analysis,
        analyzed_at=job.analyzed_at,
        application_count=application_count,
        already_applied=already_applied,
    )
