"""Application, AI screening and HITL review payloads."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationStatus, HitlDecision, Recommendation


class ApplyRequest(BaseModel):
    cover_note: Optional[str] = Field(default=None, max_length=2000)


class ScreeningOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    skills_match: float
    experience_match: float
    technology_match: float
    education_match: float
    semantic_match: float
    overall_match: float
    confidence: float
    recommendation: Recommendation
    strengths: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)
    explanation: str = ""
    evidence: List[dict] = Field(default_factory=list)
    retrieved_context: List[dict] = Field(default_factory=list)
    agent_trace: List[dict] = Field(default_factory=list)
    model_used: str = ""
    safety_notes: List[str] = Field(default_factory=list)
    created_at: datetime


class ReviewRequest(BaseModel):
    decision: HitlDecision
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    reviewer_user_id: int
    reviewer_name: Optional[str] = None
    ai_recommendation: Optional[Recommendation] = None
    ai_score: Optional[float] = None
    ai_confidence: Optional[float] = None
    decision: HitlDecision
    comment: Optional[str] = None
    overrode_ai: bool = False
    created_at: datetime


class ApplicationOut(BaseModel):
    """Used by both portals; the candidate view simply omits nothing sensitive."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ApplicationStatus
    cover_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    job_id: int
    job_title: str
    company: str
    location: Optional[str] = None

    candidate_id: int
    candidate_name: str
    candidate_email: Optional[str] = None
    candidate_location: Optional[str] = None
    candidate_years_experience: Optional[float] = None
    candidate_skills: List[str] = Field(default_factory=list)
    has_resume: bool = False

    screening: Optional[ScreeningOut] = None
    review: Optional[ReviewOut] = None


class Candidate360(BaseModel):
    """Everything the recruiter screening page renders, in one request."""

    application: ApplicationOut
    job: dict
    candidate: dict
    resume: Optional[dict] = None
    screening: Optional[ScreeningOut] = None
    reviews: List[ReviewOut] = Field(default_factory=list)


class RecruiterMetrics(BaseModel):
    total_jobs: int = 0
    active_jobs: int = 0
    total_applications: int = 0
    candidates_to_review: int = 0
    shortlisted_candidates: int = 0
    pending_hitl_reviews: int = 0


class CandidateMetrics(BaseModel):
    total_applications: int = 0
    in_screening: int = 0
    shortlisted: int = 0
    rejected: int = 0
    profile_completeness: int = 0
    has_resume: bool = False
    resume_analyzed: bool = False
