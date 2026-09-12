"""Candidate profile reads, writes and dashboard metrics.

Any profile change re-indexes the candidate in ChromaDB. Doing it here — in
the one place profiles are written — is what stops the vector store drifting
away from the database.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Candidate
from app.rag import retriever
from app.repositories import application_repo, resume_repo, user_repo
from app.schemas.candidate import CandidateOut, CandidateProfileUpdate
from app.schemas.application import CandidateMetrics

logger = logging.getLogger(__name__)


def get_profile(db: Session, user_id: int) -> Candidate:
    candidate = user_repo.get_candidate_by_user(db, user_id)
    if not candidate:
        raise NotFoundError("Candidate profile not found")
    return candidate


def update_profile(db: Session, user_id: int, payload: CandidateProfileUpdate) -> Candidate:
    candidate = get_profile(db, user_id)
    data = payload.model_dump(exclude_unset=True, mode="json")

    # `full_name` lives on the user row, not the candidate row.
    full_name = data.pop("full_name", None)
    if full_name:
        candidate.user.full_name = full_name.strip()

    for field, value in data.items():
        setattr(candidate, field, value)

    db.commit()
    db.refresh(candidate)
    reindex(db, candidate)
    return candidate


def reindex(db: Session, candidate: Candidate) -> int:
    """Refresh this candidate's chunks in the vector store.

    Never lets an indexing failure break a profile save — the profile is the
    source of truth and the index can be rebuilt.
    """
    try:
        resume = resume_repo.latest_for_candidate(db, candidate.id)
        return retriever.index_candidate(
            candidate, candidate.user, resume.extracted_text if resume else ""
        )
    except Exception as exc:
        logger.error("Failed to index candidate %s: %s", candidate.id, exc)
        return 0


def to_out(db: Session, candidate: Candidate) -> CandidateOut:
    resume = resume_repo.latest_for_candidate(db, candidate.id)
    return CandidateOut(
        id=candidate.id,
        user_id=candidate.user_id,
        full_name=candidate.user.full_name,
        email=candidate.user.email,
        phone=candidate.phone,
        location=candidate.location,
        headline=candidate.headline,
        years_experience=candidate.years_experience,
        skills=candidate.skills or [],
        education=_as_dicts(candidate.education, "degree"),
        projects=_as_dicts(candidate.projects, "name"),
        has_resume=resume is not None,
        resume_analyzed=bool(resume and resume.ai_analysis),
    )


def metrics(db: Session, candidate: Candidate) -> CandidateMetrics:
    counts = application_repo.candidate_metrics(db, candidate.id)
    resume = resume_repo.latest_for_candidate(db, candidate.id)
    return CandidateMetrics(
        **counts,
        profile_completeness=completeness(candidate, resume),
        has_resume=resume is not None,
        resume_analyzed=bool(resume and resume.ai_analysis),
    )


def completeness(candidate: Candidate, resume: Optional[object]) -> int:
    """A percentage for the dashboard's progress bar — six equal parts."""
    checks = [
        bool(candidate.phone),
        bool(candidate.location),
        bool(candidate.skills),
        candidate.years_experience is not None,
        bool(candidate.education),
        resume is not None,
    ]
    return round(sum(checks) / len(checks) * 100)


def _as_dicts(items, text_key: str) -> list:
    """Normalise a list that may hold dicts or plain strings.

    The AI import writes education and projects as strings (that is what the
    Resume Agent returns), while the profile form posts objects. The API always
    hands the frontend objects.
    """
    out = []
    for item in items or []:
        out.append(item if isinstance(item, dict) else {text_key: str(item)})
    return out
