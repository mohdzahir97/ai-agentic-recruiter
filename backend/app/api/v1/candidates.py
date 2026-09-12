"""Candidate portal endpoints.

Route order matters: `/candidates/applications` and `/candidates/me` are
declared before `/candidates/{candidate_id}`, otherwise FastAPI would match
"me" as a path parameter and fail to parse it as an int.
"""
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_candidate, require_recruiter
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models import Candidate, Recruiter
from app.repositories import application_repo, resume_repo, user_repo
from app.schemas.application import ApplicationOut, CandidateMetrics
from app.schemas.candidate import CandidateOut, CandidateProfileUpdate, ResumeOut
from app.schemas.job import RecommendedJob
from app.services import application_service, candidate_service, job_service, resume_service

router = APIRouter(prefix="/candidates", tags=["candidate"])


# --- Profile -----------------------------------------------------------------


@router.get("/me", response_model=CandidateOut)
def get_me(
    candidate: Candidate = Depends(require_candidate), db: Session = Depends(get_db)
) -> CandidateOut:
    return candidate_service.to_out(db, candidate)


@router.put("/me", response_model=CandidateOut)
def update_me(
    payload: CandidateProfileUpdate,
    candidate: Candidate = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> CandidateOut:
    updated = candidate_service.update_profile(db, candidate.user_id, payload)
    return candidate_service.to_out(db, updated)


@router.get("/me/metrics", response_model=CandidateMetrics)
def my_metrics(
    candidate: Candidate = Depends(require_candidate), db: Session = Depends(get_db)
) -> CandidateMetrics:
    return candidate_service.metrics(db, candidate)


# --- Resume ------------------------------------------------------------------


@router.post("/resume", response_model=ResumeOut, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    candidate: Candidate = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> ResumeOut:
    """Upload a PDF, extract its text and index it. Analysis is a separate call."""
    content = await file.read()
    resume = resume_service.upload(
        db,
        candidate,
        filename=file.filename or "resume.pdf",
        content=content,
        content_type=file.content_type or "application/pdf",
    )
    return resume_service.to_out(resume)


@router.get("/resume", response_model=ResumeOut)
def get_resume(
    candidate: Candidate = Depends(require_candidate), db: Session = Depends(get_db)
) -> ResumeOut:
    return resume_service.to_out(resume_service.get_latest(db, candidate))


@router.get("/resume/file")
def download_resume(
    candidate: Candidate = Depends(require_candidate), db: Session = Depends(get_db)
) -> FileResponse:
    resume = resume_service.get_latest(db, candidate)
    path, filename = resume_service.file_response_args(resume)
    return FileResponse(path, media_type="application/pdf", filename=filename)


# --- Jobs and applications ---------------------------------------------------


@router.get("/recommended-jobs", response_model=List[RecommendedJob])
def recommended_jobs(
    candidate: Candidate = Depends(require_candidate), db: Session = Depends(get_db)
) -> List[RecommendedJob]:
    """Semantic search over the job index, using this candidate as the query."""
    return job_service.recommend(db, candidate)


@router.get("/applications", response_model=List[ApplicationOut])
def my_applications(
    candidate: Candidate = Depends(require_candidate), db: Session = Depends(get_db)
) -> List[ApplicationOut]:
    return application_service.list_for_candidate(db, candidate)


@router.get("/applications/{application_id}", response_model=ApplicationOut)
def my_application(
    application_id: int,
    candidate: Candidate = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    application = application_service.get_for_candidate(db, candidate, application_id)
    return application_service.to_out(application, include_ai=False)


# --- Recruiter view of a candidate -------------------------------------------


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(
    candidate_id: int,
    recruiter: Recruiter = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> CandidateOut:
    """A recruiter may view a candidate only once they have applied to a job of theirs."""
    candidate = _visible_candidate(db, recruiter, candidate_id)
    return candidate_service.to_out(db, candidate)


@router.get("/{candidate_id}/resume/file")
def download_candidate_resume(
    candidate_id: int,
    recruiter: Recruiter = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> FileResponse:
    candidate = _visible_candidate(db, recruiter, candidate_id)
    resume = resume_repo.latest_for_candidate(db, candidate.id)
    if not resume:
        raise NotFoundError("This candidate has no resume")
    path, filename = resume_service.file_response_args(resume)
    return FileResponse(path, media_type="application/pdf", filename=filename)


def _visible_candidate(db: Session, recruiter: Recruiter, candidate_id: int) -> Candidate:
    """The access rule for recruiter-to-candidate visibility, in one place.

    Applying to a recruiter's job is what grants that recruiter access to the
    profile — a recruiter cannot browse the whole candidate database.
    """
    candidate = user_repo.get_candidate(db, candidate_id)
    if not candidate:
        raise NotFoundError("Candidate not found")
    visible_ids = {c.id for c in application_repo.distinct_candidates_for_recruiter(db, recruiter.id)}
    if candidate_id not in visible_ids:
        raise ForbiddenError("This candidate has not applied to any of your jobs")
    return candidate
