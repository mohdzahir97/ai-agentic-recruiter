"""Candidate profile and resume payloads."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EducationItem(BaseModel):
    degree: str = ""
    institution: str = ""
    year: Optional[str] = None


class ProjectItem(BaseModel):
    name: str = ""
    description: str = ""
    technologies: List[str] = Field(default_factory=list)


class CandidateProfileUpdate(BaseModel):
    """Every field optional: the profile form saves partially-filled drafts."""

    full_name: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=40)
    location: Optional[str] = Field(default=None, max_length=120)
    headline: Optional[str] = Field(default=None, max_length=200)
    years_experience: Optional[float] = Field(default=None, ge=0, le=60)
    skills: Optional[List[str]] = None
    education: Optional[List[EducationItem]] = None
    projects: Optional[List[ProjectItem]] = None


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: List[str] = Field(default_factory=list)
    education: List[dict] = Field(default_factory=list)
    projects: List[dict] = Field(default_factory=list)
    has_resume: bool = False
    resume_analyzed: bool = False


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    filename: str
    size_bytes: int
    page_count: int
    content_type: str
    created_at: datetime
    analyzed_at: Optional[datetime] = None
    analysis_model: Optional[str] = None
    ai_analysis: Optional[dict] = None
    # First part of the parsed text, so the UI can prove extraction worked
    # without shipping a whole resume to the browser on every list request.
    text_preview: Optional[str] = None
