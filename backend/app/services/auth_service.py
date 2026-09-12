"""Registration and login.

Registering creates the `User` *and* its role-specific profile row in one
transaction, so there is never an account whose role has no profile behind it.
"""
import logging

from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import UserRole
from app.repositories import user_repo
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

logger = logging.getLogger(__name__)


def register(db: Session, payload: RegisterRequest) -> TokenResponse:
    if user_repo.get_by_email(db, payload.email):
        raise ConflictError("An account with that email already exists")

    user = user_repo.create_user(
        db,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role.value,
    )

    if payload.role is UserRole.CANDIDATE:
        user_repo.create_candidate(db, user)
    else:
        user_repo.create_recruiter(db, user, payload.company)

    db.commit()
    db.refresh(user)
    logger.info("Registered %s as %s", user.email, user.role)
    return _token_response(user)


def login(db: Session, payload: LoginRequest) -> TokenResponse:
    user = user_repo.get_by_email(db, payload.email)
    # Same message for "no such user" and "wrong password": telling them apart
    # turns the login form into an account-enumeration oracle.
    if not user or not verify_password(payload.password, user.password_hash):
        raise AuthError("Incorrect email or password")
    if not user.is_active:
        raise AuthError("This account is disabled")
    return _token_response(user)


def _token_response(user) -> TokenResponse:
    token, expires_in = create_access_token(user.id, user.role)
    return TokenResponse(
        access_token=token, expires_in=expires_in, user=UserOut.model_validate(user)
    )
