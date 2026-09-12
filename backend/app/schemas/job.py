"""Job creation, update and output payloads."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import JobStatus


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    company: str = Field(min_length=1, max_length=150)
    location: Optional[str] = Field(default=None, max_length=150)
    employment_type: Optional[str] = Field(default=None, max_length=50)
    experience_required: Optional[float] = Field(default=None, ge=0, le=40)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    description: str = Field(min_length=20)


class JobUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    company: Optional[str] = Field(default=None, min_length=1, max_length=150)
    location: Optional[str] = Field(default=None, max_length=150)
    employment_type: Optional[str] = Field(default=None, max_length=50)
    experience_required: Optional[float] = Field(default=None, ge=0, le=40)
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    description: Optional[str] = Field(default=None, min_length=20)
    status: Optional[JobStatus] = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_required: Optional[float] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    description: str
    status: JobStatus
    created_at: datetime
    jd_analysis: Optional[dict] = None
    analyzed_at: Optional[datetime] = None
    application_count: int = 0
    # Set only on the candidate's job list, so the UI can disable Apply.
    already_applied: bool = False


class RecommendedJob(JobOut):
    """A job surfaced by semantic search over the candidate's own profile."""

    relevance: float = 0.0
    reason: str = ""
