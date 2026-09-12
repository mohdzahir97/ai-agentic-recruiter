"""Domain exceptions.

Services raise these instead of `HTTPException` so that the service layer
stays free of web-framework imports and can be unit-tested on its own. The
API layer translates them into HTTP responses in `main.py`.
"""


class AppError(Exception):
    """Base class for every error this application raises on purpose."""

    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    """The request is valid but clashes with existing state (duplicate apply)."""

    status_code = 409


class AuthError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    """Authenticated, but the wrong role for this endpoint."""

    status_code = 403


class ValidationError(AppError):
    status_code = 422


class AIError(AppError):
    """The AI layer could not produce a usable structured result."""

    status_code = 502
