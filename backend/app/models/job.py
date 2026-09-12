"""Job posting and the Job Agent's structured breakdown of its description."""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import JobStatus

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import Recruiter


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    recruiter_id: Mapped[int] = mapped_column(
        ForeignKey("recruiters.id", ondelete="CASCADE"), index=True, nullable=False
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(150))
    employment_type: Mapped[Optional[str]] = mapped_column(String(50))
    experience_required: Mapped[Optional[float]] = mapped_column()

    # Skills the recruiter typed in. The Job Agent may add more it finds in the
    # description; the two are kept apart so the agent can never silently
    # overwrite what a human explicitly asked for.
    required_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default=JobStatus.ACTIVE.value)

    jd_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    analysis_model: Mapped[Optional[str]] = mapped_column(String(120))

    recruiter: Mapped["Recruiter"] = relationship(back_populates="jobs")
    applications: Mapped[List["Application"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
