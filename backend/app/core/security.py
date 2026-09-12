"""Password hashing (bcrypt) and JWT issue/verify.

The only module that imports `bcrypt` or `jose`. Everything else depends on
these four functions, so the token or hashing scheme can change without
touching the services.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import AuthError

# bcrypt refuses inputs longer than 72 bytes rather than truncating them, so
# long passphrases would raise instead of hashing. Truncate explicitly.
_BCRYPT_MAX_BYTES = 72


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_encode(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_encode(plain), hashed.encode("utf-8"))
    except ValueError:
        # Stored hash is not a valid bcrypt hash — treat as a failed login
        # rather than a 500.
        return False


def _encode(plain: str) -> bytes:
    return plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    """Return `(token, expires_in_seconds)`.

    The role is embedded in the token so RBAC checks do not need a database
    round-trip on every request — but the user row is still loaded, so a
    deactivated account cannot keep using an unexpired token.
    """
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AuthError("Invalid or expired token") from exc
