"""Enumerations shared by the models, schemas and the frontend.

These are stored as plain strings rather than native database enums: adding a
value later is then a code change instead of a migration, which matters while
the workflow is still being designed.
"""
import enum


class UserRole(str, enum.Enum):
    CANDIDATE = "CANDIDATE"
    RECRUITER = "RECRUITER"


class JobStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class ApplicationStatus(str, enum.Enum):
    """The Phase 1 lifecycle: APPLIED -> SCREENING -> SHORTLISTED/ON_HOLD/REJECTED."""

    APPLIED = "APPLIED"
    SCREENING = "SCREENING"
    SHORTLISTED = "SHORTLISTED"
    ON_HOLD = "ON_HOLD"
    REJECTED = "REJECTED"


class Recommendation(str, enum.Enum):
    """What the AI suggests. It is advice only — see `HitlDecision`."""

    STRONG_MATCH = "STRONG_MATCH"
    GOOD_MATCH = "GOOD_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    WEAK_MATCH = "WEAK_MATCH"


class HitlDecision(str, enum.Enum):
    """The human decision. Only this changes an application's outcome."""

    SHORTLIST = "SHORTLIST"
    HOLD = "HOLD"
    REJECT = "REJECT"


# The single place that maps a human decision onto the application lifecycle.
DECISION_TO_STATUS = {
    HitlDecision.SHORTLIST: ApplicationStatus.SHORTLISTED,
    HitlDecision.HOLD: ApplicationStatus.ON_HOLD,
    HitlDecision.REJECT: ApplicationStatus.REJECTED,
}
