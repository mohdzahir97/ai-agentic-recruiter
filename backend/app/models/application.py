"""Application, AI screening result and the human review that decides it.

Three separate tables on purpose:

* `applications` holds the state a candidate sees.
* `ai_screenings` holds what the AI produced — advisory, append-only history.
* `hitl_reviews` holds what a human decided, including the AI's suggestion at
  the time, so an override is visible in the record rather than inferred.

Only a `HitlReview` may move an application to a terminal status.
"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ApplicationStatus

if TYPE_CHECKING:  # resolved by SQLAlchemy at mapper configuration time
    from app.models.job import Job
    from app.models.user import Candidate, User


class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    # One application per candidate per job — the database enforces it so a
    # double-clicked Apply button cannot create a duplicate.
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_application_job_candidate"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[str] = mapped_column(String(20), default=ApplicationStatus.APPLIED.value)
    cover_note: Mapped[Optional[str]] = mapped_column(Text)

    job: Mapped["Job"] = relationship(back_populates="applications")
    candidate: Mapped["Candidate"] = relationship(back_populates="applications")
    screenings: Mapped[List["AIScreening"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="AIScreening.id.desc()",
    )
    reviews: Mapped[List["HitlReview"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="HitlReview.id.desc()",
    )

    @property
    def latest_screening(self) -> Optional["AIScreening"]:
        return self.screenings[0] if self.screenings else None

    @property
    def latest_review(self) -> Optional["HitlReview"]:
        return self.reviews[0] if self.reviews else None


class AIScreening(Base, TimestampMixin):
    __tablename__ = "ai_screenings"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Percentages, 0-100.
    skills_match: Mapped[float] = mapped_column(Float, default=0.0)
    experience_match: Mapped[float] = mapped_column(Float, default=0.0)
    technology_match: Mapped[float] = mapped_column(Float, default=0.0)
    education_match: Mapped[float] = mapped_column(Float, default=0.0)
    semantic_match: Mapped[float] = mapped_column(Float, default=0.0)
    overall_match: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    recommendation: Mapped[str] = mapped_column(String(30), nullable=False)
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    skill_gaps: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text, default="")

    # Quoted resume/JD snippets backing each claim, so a recruiter can check
    # the AI rather than take its word (spec section 16: always give evidence).
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    # The chunks the retriever returned, kept for explainability and debugging.
    retrieved_context: Mapped[list] = mapped_column(JSON, default=list)
    # The agent's own trace: goal -> plan -> execute -> evaluate.
    agent_trace: Mapped[list] = mapped_column(JSON, default=list)

    model_used: Mapped[str] = mapped_column(String(120), default="")
    safety_notes: Mapped[list] = mapped_column(JSON, default=list)

    application: Mapped["Application"] = relationship(back_populates="screenings")
    reviews: Mapped[List["HitlReview"]] = relationship(back_populates="screening")


class HitlReview(Base, TimestampMixin):
    """A human decision. The AI figures are copied in, not joined.

    Copying freezes what the AI said *at the moment the human decided*. A later
    re-screen then cannot rewrite the history of why someone was rejected.
    """

    __tablename__ = "hitl_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    screening_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ai_screenings.id", ondelete="SET NULL")
    )
    reviewer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    ai_recommendation: Mapped[Optional[str]] = mapped_column(String(30))
    ai_score: Mapped[Optional[float]] = mapped_column(Float)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float)

    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    # True when the human went against the AI's suggestion. Worth storing
    # rather than recomputing: it is the number you want when asking "how often
    # is the model actually trusted?".
    overrode_ai: Mapped[bool] = mapped_column(default=False)

    application: Mapped["Application"] = relationship(back_populates="reviews")
    screening: Mapped[Optional["AIScreening"]] = relationship(back_populates="reviews")
    # Read-only: the reviewer's name is shown in the decision history. `User`
    # deliberately has no `reviews` back-reference — a user does not need to
    # load every decision they have ever made.
    reviewer: Mapped["User"] = relationship("User", lazy="joined")
