"""Users, candidate profiles and recruiter profiles."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate, Recruiter, User


def get_by_email(db: Session, email: str) -> Optional[User]:
    # Emails are stored lower-cased at registration so this comparison is a
    # plain index lookup rather than a function scan.
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def get_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def create_user(db: Session, *, email: str, password_hash: str, full_name: str, role: str) -> User:
    user = User(
        email=email.strip().lower(),
        password_hash=password_hash,
        full_name=full_name.strip(),
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def create_candidate(db: Session, user: User) -> Candidate:
    candidate = Candidate(user_id=user.id, skills=[], education=[], projects=[])
    db.add(candidate)
    db.flush()
    return candidate


def create_recruiter(db: Session, user: User, company: Optional[str]) -> Recruiter:
    recruiter = Recruiter(user_id=user.id, company=company)
    db.add(recruiter)
    db.flush()
    return recruiter


def get_candidate_by_user(db: Session, user_id: int) -> Optional[Candidate]:
    return db.scalar(select(Candidate).where(Candidate.user_id == user_id))


def get_candidate(db: Session, candidate_id: int) -> Optional[Candidate]:
    return db.get(Candidate, candidate_id)


def get_recruiter_by_user(db: Session, user_id: int) -> Optional[Recruiter]:
    return db.scalar(select(Recruiter).where(Recruiter.user_id == user_id))
