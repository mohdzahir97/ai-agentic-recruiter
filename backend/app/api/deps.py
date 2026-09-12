"""Authentication and RBAC dependencies.

`get_current_user` proves who you are; `require_candidate` and
`require_recruiter` prove you may be here. Every protected route declares one
of the two, so a route's access rules are visible in its signature rather than
buried in its body.
"""
from typing import Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, ForbiddenError
from app.core.security import decode_token
from app.db.session import get_db
from app.models import Candidate, Recruiter, User, UserRole
from app.repositories import user_repo


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("Not authenticated")

    payload = decode_token(token)
    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        raise AuthError("Invalid token subject")

    # The user is loaded rather than trusted from the token, so deactivating an
    # account takes effect immediately instead of when the token expires.
    user = user_repo.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise AuthError("Account not found or disabled")
    return user


def require_candidate(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Candidate:
    if user.role != UserRole.CANDIDATE.value:
        raise ForbiddenError("This area is for candidates")
    candidate = user_repo.get_candidate_by_user(db, user.id)
    if not candidate:
        raise ForbiddenError("Candidate profile is missing")
    return candidate


def require_recruiter(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Recruiter:
    if user.role != UserRole.RECRUITER.value:
        raise ForbiddenError("This area is for recruiters")
    recruiter = user_repo.get_recruiter_by_user(db, user.id)
    if not recruiter:
        raise ForbiddenError("Recruiter profile is missing")
    return recruiter


def optional_candidate(
    request: Request, db: Session = Depends(get_db)
) -> Optional[Candidate]:
    """For the public job list, which is richer when we know who is looking.

    Returns None instead of raising when there is no token, so a recruiter (or
    a signed-out visitor) can browse jobs without hitting a 401.
    """
    try:
        user = get_current_user(request, db)
    except AuthError:
        return None
    if user.role != UserRole.CANDIDATE.value:
        return None
    return user_repo.get_candidate_by_user(db, user.id)
