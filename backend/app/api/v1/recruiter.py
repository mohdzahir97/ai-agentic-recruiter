"""Recruiter dashboard, job list, candidate list and screening queue."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_recruiter
from app.db.session import get_db
from app.models import Recruiter
from app.repositories import application_repo
from app.schemas.application import ApplicationOut, RecruiterMetrics
from app.schemas.candidate import CandidateOut
from app.schemas.job import JobOut
from app.services import application_service, candidate_service, job_service

router = APIRouter(prefix="/recruiter", tags=["recruiter"])


@router.get("/metrics", response_model=RecruiterMetrics)
def metrics(
    recruiter: Recruiter = Depends(require_recruiter), db: Session = Depends(get_db)
) -> RecruiterMetrics:
    """The five dashboard numbers from spec section 3, plus the HITL backlog."""
    return RecruiterMetrics(**application_repo.recruiter_metrics(db, recruiter.id))


@router.get("/jobs", response_model=List[JobOut])
def my_jobs(
    recruiter: Recruiter = Depends(require_recruiter), db: Session = Depends(get_db)
) -> List[JobOut]:
    return job_service.list_for_recruiter(db, recruiter)


@router.get("/applications", response_model=List[ApplicationOut])
def all_applications(
    status: Optional[str] = Query(None, description="Filter by application status"),
    recruiter: Recruiter = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> List[ApplicationOut]:
    return application_service.list_for_recruiter(db, recruiter, status)


@router.get("/screening-queue", response_model=List[ApplicationOut])
def screening_queue(
    recruiter: Recruiter = Depends(require_recruiter), db: Session = Depends(get_db)
) -> List[ApplicationOut]:
    """Applications still waiting on a human.

    Screened-but-undecided first (the AI has done its part and a person is the
    bottleneck), then the ones not yet screened.
    """
    applications = application_service.list_for_recruiter(db, recruiter)
    pending = [a for a in applications if a.review is None]
    pending.sort(key=lambda a: (a.screening is None, -(a.screening.overall_match if a.screening else 0)))
    return pending


@router.get("/candidates", response_model=List[CandidateOut])
def my_candidates(
    recruiter: Recruiter = Depends(require_recruiter), db: Session = Depends(get_db)
) -> List[CandidateOut]:
    """Everyone who has applied to one of this recruiter's jobs."""
    return [
        candidate_service.to_out(db, candidate)
        for candidate in application_repo.distinct_candidates_for_recruiter(db, recruiter.id)
    ]
