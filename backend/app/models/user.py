"""Account, candidate profile and recruiter profile.

One `User` row holds the credentials and the role; the role-specific fields
live in `Candidate` or `Recruiter`. Keeping them apart means a candidate row
never carries empty recruiter columns, and RBAC has exactly one field to read.
"""
from typing import List, Optional

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import UserRole


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    candidate: Mapped[Optional["Candidate"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    recruiter: Mapped[Optional["Recruiter"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def is_candidate(self) -> bool:
        return self.role == UserRole.CANDIDATE.value

    @property
    def is_recruiter(self) -> bool:
        return self.role == UserRole.RECRUITER.value


class Candidate(Base, TimestampMixin):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    phone: Mapped[Optional[str]] = mapped_column(String(40))
    location: Mapped[Optional[str]] = mapped_column(String(120))
    headline: Mapped[Optional[str]] = mapped_column(String(200))
    years_experience: Mapped[Optional[float]] = mapped_column()

    # Free-form lists. JSON keeps the schema small and works identically on
    # Postgres and SQLite; a normalised skills table would be the next step if
    # skills ever needed to be queried or ranked in SQL.
    skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    education: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)

    user: Mapped["User"] = relationship(back_populates="candidate")
    resumes: Mapped[List["Resume"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", order_by="Resume.id.desc()"
    )
    applications: Mapped[List["Application"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )

    @property
    def current_resume(self) -> Optional["Resume"]:
        """The most recently uploaded resume — the one the AI layer uses."""
        return self.resumes[0] if self.resumes else None


class Recruiter(Base, TimestampMixin):
    __tablename__ = "recruiters"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    company: Mapped[Optional[str]] = mapped_column(String(150))
    title: Mapped[Optional[str]] = mapped_column(String(120))

    user: Mapped["User"] = relationship(back_populates="recruiter")
    jobs: Mapped[List["Job"]] = relationship(
        back_populates="recruiter", cascade="all, delete-orphan"
    )


from app.models.application import Application  # noqa: E402,F401
from app.models.job import Job  # noqa: E402,F401
from app.models.resume import Resume  # noqa: E402,F401
