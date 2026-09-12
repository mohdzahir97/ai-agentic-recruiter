"""Resume upload, text extraction, AI analysis and indexing.

    upload -> validate -> store file -> extract text -> index for RAG
                                                     -> Resume Agent (structured JSON)

Extraction happens on upload so a resume is searchable immediately; the AI
analysis is a separate step, because it is the slow and fallible one and the
candidate should not be left staring at a spinner to see their file arrived.
"""
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.agents import resume_agent
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models import Candidate, Resume
from app.rag.pdf_loader import extract_pdf_text
from app.repositories import resume_repo
from app.schemas.candidate import ResumeOut
from app.services import candidate_service

logger = logging.getLogger(__name__)

PREVIEW_CHARS = 1200


def upload(
    db: Session, candidate: Candidate, *, filename: str, content: bytes, content_type: str
) -> Resume:
    settings = get_settings()

    if not filename.lower().endswith(".pdf"):
        raise ValidationError("Only PDF resumes are supported")
    if not content:
        raise ValidationError("The uploaded file is empty")
    if len(content) > settings.max_upload_bytes:
        raise ValidationError(f"Resume must be smaller than {settings.max_upload_size_mb} MB")

    # Store under a generated name: two candidates uploading "resume.pdf" must
    # not collide, and the original name must never reach the filesystem.
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    stored_name = f"candidate_{candidate.id}_{uuid.uuid4().hex}.pdf"
    stored_path = settings.upload_path / stored_name
    stored_path.write_bytes(content)

    try:
        text, page_count = extract_pdf_text(stored_path)
    except ValidationError:
        stored_path.unlink(missing_ok=True)  # nothing usable — do not keep it
        raise

    resume = Resume(
        candidate_id=candidate.id,
        filename=Path(filename).name,
        stored_path=str(stored_path),
        content_type=content_type or "application/pdf",
        size_bytes=len(content),
        extracted_text=text,
        page_count=page_count,
    )
    resume_repo.add(db, resume)
    db.commit()
    db.refresh(resume)

    candidate_service.reindex(db, candidate)
    logger.info("Stored resume %s for candidate %s (%d chars)", resume.id, candidate.id, len(text))
    return resume


def analyze(db: Session, candidate: Candidate, resume: Optional[Resume] = None) -> Resume:
    """Run the Resume Agent and store its structured output."""
    resume = resume or resume_repo.latest_for_candidate(db, candidate.id)
    if not resume:
        raise NotFoundError("Upload a resume first")

    analysis, model = resume_agent.analyze_resume(resume.extracted_text or "")
    resume.ai_analysis = analysis.model_dump(mode="json")
    resume.analysis_model = model
    resume.analyzed_at = datetime.now(timezone.utc)

    _fill_empty_profile_fields(candidate, analysis)

    db.commit()
    db.refresh(resume)
    candidate_service.reindex(db, candidate)
    return resume


def _fill_empty_profile_fields(candidate: Candidate, analysis) -> None:
    """Pre-fill the profile from the resume — but only where it is still blank.

    The candidate's own entry always wins. The AI proposes; it never
    overwrites something a person typed.
    """
    if not candidate.skills:
        candidate.skills = analysis.skills + analysis.technologies
    if candidate.years_experience is None and analysis.experience_years:
        candidate.years_experience = analysis.experience_years
    if not candidate.education and analysis.education:
        candidate.education = [{"degree": item} for item in analysis.education]
    if not candidate.projects and analysis.projects:
        candidate.projects = [{"name": item, "description": ""} for item in analysis.projects]
    if not candidate.headline and analysis.current_title:
        candidate.headline = analysis.current_title
    if not candidate.location and analysis.location:
        candidate.location = analysis.location


def get_latest(db: Session, candidate: Candidate) -> Resume:
    resume = resume_repo.latest_for_candidate(db, candidate.id)
    if not resume:
        raise NotFoundError("No resume uploaded yet")
    return resume


def file_response_args(resume: Resume) -> Tuple[Path, str]:
    path = Path(resume.stored_path)
    if not path.exists():
        raise NotFoundError("The stored resume file is missing")
    return path, resume.filename


def to_out(resume: Resume) -> ResumeOut:
    return ResumeOut(
        id=resume.id,
        candidate_id=resume.candidate_id,
        filename=resume.filename,
        size_bytes=resume.size_bytes,
        page_count=resume.page_count,
        content_type=resume.content_type,
        created_at=resume.created_at,
        analyzed_at=resume.analyzed_at,
        analysis_model=resume.analysis_model,
        ai_analysis=resume.ai_analysis,
        text_preview=(resume.extracted_text or "")[:PREVIEW_CHARS],
    )
