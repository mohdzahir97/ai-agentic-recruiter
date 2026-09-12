"""Resumes."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Resume


def get(db: Session, resume_id: int) -> Optional[Resume]:
    return db.get(Resume, resume_id)


def latest_for_candidate(db: Session, candidate_id: int) -> Optional[Resume]:
    return db.scalar(
        select(Resume)
        .where(Resume.candidate_id == candidate_id)
        .order_by(Resume.id.desc())
        .limit(1)
    )


def list_for_candidate(db: Session, candidate_id: int) -> List[Resume]:
    return list(
        db.scalars(
            select(Resume).where(Resume.candidate_id == candidate_id).order_by(Resume.id.desc())
        )
    )


def add(db: Session, resume: Resume) -> Resume:
    db.add(resume)
    db.flush()
    return resume
