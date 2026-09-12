"""Applications, screenings and reviews.

Every list query eager-loads the job, the candidate and the latest screening
and review, because the response schema needs all four. Without that, a page
of 20 applications is 80 queries.
"""
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AIScreening,
    Application,
    ApplicationStatus,
    Candidate,
    HitlReview,
    Job,
)

_EAGER = (
    selectinload(Application.job),
    selectinload(Application.candidate).selectinload(Candidate.user),
    selectinload(Application.candidate).selectinload(Candidate.resumes),
    selectinload(Application.screenings),
    selectinload(Application.reviews),
)


def get(db: Session, application_id: int) -> Optional[Application]:
    return db.scalar(
        select(Application).where(Application.id == application_id).options(*_EAGER)
    )


def get_by_job_and_candidate(db: Session, job_id: int, candidate_id: int) -> Optional[Application]:
    return db.scalar(
        select(Application).where(
            Application.job_id == job_id, Application.candidate_id == candidate_id
        )
    )


def list_for_candidate(db: Session, candidate_id: int) -> List[Application]:
    return list(
        db.scalars(
            select(Application)
            .where(Application.candidate_id == candidate_id)
            .order_by(Application.created_at.desc())
            .options(*_EAGER)
        )
    )


def list_for_job(db: Session, job_id: int) -> List[Application]:
    return list(
        db.scalars(
            select(Application)
            .where(Application.job_id == job_id)
            .order_by(Application.created_at.desc())
            .options(*_EAGER)
        )
    )


def list_for_recruiter(
    db: Session, recruiter_id: int, status: Optional[str] = None
) -> List[Application]:
    """Every application across every job this recruiter owns."""
    stmt = (
        select(Application)
        .join(Job, Application.job_id == Job.id)
        .where(Job.recruiter_id == recruiter_id)
        .order_by(Application.created_at.desc())
        .options(*_EAGER)
    )
    if status:
        stmt = stmt.where(Application.status == status)
    return list(db.scalars(stmt))


def recruiter_owns_application(db: Session, recruiter_id: int, application_id: int) -> bool:
    """The RBAC check for every recruiter endpoint that names an application."""
    return (
        db.scalar(
            select(func.count(Application.id))
            .join(Job, Application.job_id == Job.id)
            .where(Application.id == application_id, Job.recruiter_id == recruiter_id)
        )
        or 0
    ) > 0


def recruiter_metrics(db: Session, recruiter_id: int) -> dict:
    """The dashboard numbers, in one pass over this recruiter's applications."""
    from app.models import JobStatus

    total_jobs = db.scalar(
        select(func.count(Job.id)).where(Job.recruiter_id == recruiter_id)
    ) or 0
    active_jobs = db.scalar(
        select(func.count(Job.id)).where(
            Job.recruiter_id == recruiter_id, Job.status == JobStatus.ACTIVE.value
        )
    ) or 0

    rows = db.execute(
        select(Application.status, func.count(Application.id))
        .join(Job, Application.job_id == Job.id)
        .where(Job.recruiter_id == recruiter_id)
        .group_by(Application.status)
    ).all()
    by_status = {status: count for status, count in rows}
    total_applications = sum(by_status.values())

    # "Candidates to review" = applied or screening, i.e. no human has decided
    # yet. "Pending HITL" is the subset that has an AI result waiting on a human.
    to_review = by_status.get(ApplicationStatus.APPLIED.value, 0) + by_status.get(
        ApplicationStatus.SCREENING.value, 0
    )
    pending_hitl = db.scalar(
        select(func.count(func.distinct(Application.id)))
        .join(Job, Application.job_id == Job.id)
        .join(AIScreening, AIScreening.application_id == Application.id)
        .outerjoin(HitlReview, HitlReview.application_id == Application.id)
        .where(Job.recruiter_id == recruiter_id, HitlReview.id.is_(None))
    ) or 0

    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "candidates_to_review": to_review,
        "shortlisted_candidates": by_status.get(ApplicationStatus.SHORTLISTED.value, 0),
        "pending_hitl_reviews": pending_hitl,
    }


def candidate_metrics(db: Session, candidate_id: int) -> dict:
    rows = db.execute(
        select(Application.status, func.count(Application.id))
        .where(Application.candidate_id == candidate_id)
        .group_by(Application.status)
    ).all()
    by_status = {status: count for status, count in rows}
    return {
        "total_applications": sum(by_status.values()),
        "in_screening": by_status.get(ApplicationStatus.SCREENING.value, 0),
        "shortlisted": by_status.get(ApplicationStatus.SHORTLISTED.value, 0),
        "rejected": by_status.get(ApplicationStatus.REJECTED.value, 0),
    }


def applied_job_ids(db: Session, candidate_id: int) -> set:
    return set(
        db.scalars(select(Application.job_id).where(Application.candidate_id == candidate_id))
    )


def distinct_candidates_for_recruiter(db: Session, recruiter_id: int) -> List[Candidate]:
    """Everyone who has applied to one of this recruiter's jobs."""
    return list(
        db.scalars(
            select(Candidate)
            .join(Application, Application.candidate_id == Candidate.id)
            .join(Job, Application.job_id == Job.id)
            .where(Job.recruiter_id == recruiter_id)
            .distinct()
            .options(selectinload(Candidate.user), selectinload(Candidate.resumes))
        )
    )


def add(db: Session, obj) -> object:
    db.add(obj)
    db.flush()
    return obj
