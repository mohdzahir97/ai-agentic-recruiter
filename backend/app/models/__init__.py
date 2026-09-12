"""Import every model so `Base.metadata` is complete before `create_all`."""
from app.models.application import AIScreening, Application, HitlReview
from app.models.enums import (
    ApplicationStatus,
    DECISION_TO_STATUS,
    HitlDecision,
    JobStatus,
    Recommendation,
    UserRole,
)
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import Candidate, Recruiter, User

__all__ = [
    "AIScreening",
    "Application",
    "ApplicationStatus",
    "Candidate",
    "DECISION_TO_STATUS",
    "HitlDecision",
    "HitlReview",
    "Job",
    "JobStatus",
    "Recommendation",
    "Recruiter",
    "Resume",
    "User",
    "UserRole",
]
