"""Uploaded resume plus the structured analysis produced from it.

The extracted text is kept alongside the file so re-running the AI analysis
never needs to re-parse the PDF, and so the RAG indexer has a single source
of truth for what the candidate's document actually says.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import Candidate


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="application/pdf")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)

    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    page_count: Mapped[int] = mapped_column(Integer, default=0)

    # The Resume Agent's structured output. Null until /ai/resume/analyze runs.
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    analysis_model: Mapped[Optional[str]] = mapped_column(String(120))

    candidate: Mapped["Candidate"] = relationship(back_populates="resumes")
