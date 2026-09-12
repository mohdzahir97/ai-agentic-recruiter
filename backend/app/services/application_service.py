"""Applying to jobs and shaping applications for both portals."""
import logging
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models import Application, ApplicationStatus, Candidate, JobStatus, Recruiter
from app.repositories import application_repo, job_repo, resume_repo
from app.schemas.application import ApplicationOut, ReviewOut, ScreeningOut

logger = logging.getLogger(__name__)


def apply(db: Session, candidate: Candidate, job_id: int, cover_note: Optional[str]) -> Application:
    job = job_repo.get(db, job_id)
    if not job:
        raise NotFoundError("Job not found")
    if job.status != JobStatus.ACTIVE.value:
        raise ValidationError("This job is no longer accepting applications")
    if not resume_repo.latest_for_candidate(db, candidate.id):
        # Screening has nothing to work with without one, so this is a real
        # requirement rather than a nag.
        raise ValidationError("Upload your resume before applying")
    if application_repo.get_by_job_and_candidate(db, job_id, candidate.id):
        raise ConflictError("You have already applied to this job")

    application = Application(
        job_id=job_id,
        candidate_id=candidate.id,
        cover_note=cover_note,
        status=ApplicationStatus.APPLIED.value,
    )
    db.add(application)
    try:
        db.commit()
    except IntegrityError:
        # The unique constraint caught a race the check above could not.
        db.rollback()
        raise ConflictError("You have already applied to this job")
    db.refresh(application)
    return application


def get_for_recruiter(db: Session, recruiter: Recruiter, application_id: int) -> Application:
    application = application_repo.get(db, application_id)
    if not application:
        raise NotFoundError("Application not found")
    if application.job.recruiter_id != recruiter.id:
        raise ForbiddenError("This application is for another recruiter's job")
    return application


def get_for_candidate(db: Session, candidate: Candidate, application_id: int) -> Application:
    application = application_repo.get(db, application_id)
    if not application:
        raise NotFoundError("Application not found")
    if application.candidate_id != candidate.id:
        raise ForbiddenError("This application belongs to another candidate")
    return application


def list_for_candidate(db: Session, candidate: Candidate) -> List[ApplicationOut]:
    return [
        to_out(application, include_ai=False)
        for application in application_repo.list_for_candidate(db, candidate.id)
    ]


def list_for_recruiter(
    db: Session, recruiter: Recruiter, status: Optional[str] = None
) -> List[ApplicationOut]:
    return [
        to_out(application)
        for application in application_repo.list_for_recruiter(db, recruiter.id, status)
    ]


def list_for_job(db: Session, recruiter: Recruiter, job_id: int) -> List[ApplicationOut]:
    job = job_repo.get(db, job_id)
    if not job:
        raise NotFoundError("Job not found")
    if job.recruiter_id != recruiter.id:
        raise ForbiddenError("This job belongs to another recruiter")
    return [to_out(application) for application in application_repo.list_for_job(db, job_id)]


def to_out(application: Application, include_ai: bool = True) -> ApplicationOut:
    """One shape for both portals.

    `include_ai=False` for the candidate's own list: a candidate sees their
    status, not the recruiter's screening notes about them.
    """
    candidate = application.candidate
    screening = application.latest_screening
    review = application.latest_review

    return ApplicationOut(
        id=application.id,
        status=application.status,
        cover_note=application.cover_note,
        created_at=application.created_at,
        updated_at=application.updated_at,
        job_id=application.job_id,
        job_title=application.job.title,
        company=application.job.company,
        location=application.job.location,
        candidate_id=candidate.id,
        candidate_name=candidate.user.full_name,
        candidate_email=candidate.user.email if include_ai else None,
        candidate_location=candidate.location,
        candidate_years_experience=candidate.years_experience,
        candidate_skills=candidate.skills or [],
        has_resume=bool(candidate.resumes),
        screening=screening_out(screening) if include_ai and screening else None,
        review=review_out(review) if include_ai and review else None,
    )


def screening_out(screening) -> ScreeningOut:
    return ScreeningOut.model_validate(screening)


def review_out(review) -> ReviewOut:
    out = ReviewOut.model_validate(review)
    # The reviewer's name is on the user row; the ORM object does not carry it.
    reviewer = getattr(review, "reviewer", None)
    if reviewer is not None:
        out.reviewer_name = reviewer.full_name
    return out
