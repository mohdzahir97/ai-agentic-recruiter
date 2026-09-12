"""Job endpoints — browsing (candidates) and management (recruiters)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import optional_candidate, require_candidate, require_recruiter
from app.db.session import get_db
from app.models import Candidate, Recruiter
from app.schemas.application import ApplicationOut, ApplyRequest
from app.schemas.job import JobCreate, JobOut, JobUpdate
from app.services import application_service, job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=List[JobOut])
def list_jobs(
    search: str = Query("", max_length=120),
    candidate: Optional[Candidate] = Depends(optional_candidate),
    db: Session = Depends(get_db),
) -> List[JobOut]:
    """Active jobs. When a candidate is signed in, each is flagged if applied to."""
    return job_service.list_open(db, candidate, search)


@router.post("", response_model=JobOut, status_code=201)
def create_job(
    payload: JobCreate,
    recruiter: Recruiter = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> JobOut:
    """Create a job. The Job Agent analyses the description as part of this call."""
    job = job_service.create(db, recruiter, payload)
    return job_service.to_out(db, job)


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    candidate: Optional[Candidate] = Depends(optional_candidate),
    db: Session = Depends(get_db),
) -> JobOut:
    return job_service.to_out(db, job_service.get(db, job_id), candidate)


@router.put("/{job_id}", response_model=JobOut)
def update_job(
    job_id: int,
    payload: JobUpdate,
    recruiter: Recruiter = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> JobOut:
    job = job_service.update(db, recruiter, job_id, payload)
    return job_service.to_out(db, job)


@router.post("/{job_id}/apply", response_model=ApplicationOut, status_code=201)
def apply_to_job(
    job_id: int,
    payload: ApplyRequest,
    candidate: Candidate = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    application = application_service.apply(db, candidate, job_id, payload.cover_note)
    return application_service.to_out(application, include_ai=False)


@router.get("/{job_id}/applications", response_model=List[ApplicationOut])
def job_applications(
    job_id: int,
    recruiter: Recruiter = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> List[ApplicationOut]:
    return application_service.list_for_job(db, recruiter, job_id)
