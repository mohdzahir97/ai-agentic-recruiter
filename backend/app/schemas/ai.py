"""Structured outputs for the three agents.

These models are the contract between the LLM and the rest of the
application. Section 5 of the spec is explicit about this: where structured
data is required, we never keep free-form text — the model is asked to fill
one of these shapes, and anything that does not validate is rejected and
retried rather than parsed by hand.
"""
from typing import List

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Recommendation


def _clamp_percent(value: float) -> float:
    """LLMs happily return 0.93 for "93%" or 105 for "very high"."""
    if value is None:
        return 0.0
    value = float(value)
    if 0 < value <= 1:
        value *= 100
    return round(max(0.0, min(100.0, value)), 1)


class ResumeAnalysis(BaseModel):
    """The Resume Agent's output — the example JSON in spec section 5."""

    skills: List[str] = Field(default_factory=list, description="Professional skills, e.g. 'REST API design'")
    technologies: List[str] = Field(default_factory=list, description="Named tools/platforms, e.g. 'Docker'")
    experience_years: float = Field(default=0.0, description="Total professional experience in years")
    education: List[str] = Field(default_factory=list, description="Degrees, e.g. 'B.Tech Computer Science'")
    projects: List[str] = Field(default_factory=list, description="Project names with a one-line summary")
    certifications: List[str] = Field(default_factory=list)
    summary: str = Field(default="", description="Two-sentence professional summary")
    current_title: str = Field(default="")
    location: str = Field(default="")

    @field_validator("experience_years")
    @classmethod
    def _sane_years(cls, v: float) -> float:
        return round(max(0.0, min(60.0, float(v or 0))), 1)


class JobAnalysis(BaseModel):
    """The Job Agent's output — spec section 4."""

    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    experience_requirement: str = Field(default="", description="As written, e.g. '5+ years backend'")
    minimum_years: float = Field(default=0.0)
    education_requirement: str = Field(default="")
    responsibilities: List[str] = Field(default_factory=list)
    seniority: str = Field(default="", description="e.g. Junior / Mid / Senior")

    @field_validator("minimum_years")
    @classmethod
    def _sane_years(cls, v: float) -> float:
        return round(max(0.0, min(40.0, float(v or 0))), 1)


class Evidence(BaseModel):
    """One claim tied to the text it came from."""

    claim: str
    source: str = Field(default="resume", description="resume | profile | job")
    quote: str = Field(default="", description="Short verbatim snippet supporting the claim")


class MatchResult(BaseModel):
    """The Matching Agent's output — spec section 7."""

    skills_match: float = 0.0
    experience_match: float = 0.0
    technology_match: float = 0.0
    education_match: float = 0.0
    semantic_match: float = 0.0
    overall_match: float = 0.0
    confidence: float = 0.0

    recommendation: Recommendation = Recommendation.PARTIAL_MATCH
    strengths: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)
    explanation: str = ""
    evidence: List[Evidence] = Field(default_factory=list)

    @field_validator(
        "skills_match",
        "experience_match",
        "technology_match",
        "education_match",
        "semantic_match",
        "overall_match",
        "confidence",
        mode="before",
    )
    @classmethod
    def _percent(cls, v):
        return _clamp_percent(v)


class AnalyzeTextRequest(BaseModel):
    """Ad-hoc analysis endpoint — lets you try the agents without a DB row."""

    text: str = Field(min_length=20)


class ScreeningRequest(BaseModel):
    # Re-screening is explicit so an accidental double click does not spend
    # another LLM call when a result already exists.
    force: bool = False
