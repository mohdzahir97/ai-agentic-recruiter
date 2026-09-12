"""Jobs and their application counts."""
from typing import Dict, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Application, Job, JobStatus


def get(db: Session, job_id: int) -> Optional[Job]:
    return db.get(Job, job_id)


def list_active(db: Session, search: str = "") -> List[Job]:
    stmt = select(Job).where(Job.status == JobStatus.ACTIVE.value)
    if search.strip():
        pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            func.lower(Job.title).like(pattern)
            | func.lower(Job.company).like(pattern)
            | func.lower(Job.location).like(pattern)
        )
    return list(db.scalars(stmt.order_by(Job.created_at.desc())))


def list_for_recruiter(db: Session, recruiter_id: int) -> List[Job]:
    return list(
        db.scalars(
            select(Job)
            .where(Job.recruiter_id == recruiter_id)
            .order_by(Job.created_at.desc())
            .options(selectinload(Job.applications))
        )
    )


def list_by_ids(db: Session, job_ids: Sequence[int]) -> List[Job]:
    if not job_ids:
        return []
    return list(db.scalars(select(Job).where(Job.id.in_(job_ids))))


def application_counts(db: Session, job_ids: Sequence[int]) -> Dict[int, int]:
    """One grouped query instead of a count per job (the N+1 this replaces)."""
    if not job_ids:
        return {}
    rows = db.execute(
        select(Application.job_id, func.count(Application.id))
        .where(Application.job_id.in_(job_ids))
        .group_by(Application.job_id)
    ).all()
    return {job_id: count for job_id, count in rows}


def add(db: Session, job: Job) -> Job:
    db.add(job)
    db.flush()
    return job
