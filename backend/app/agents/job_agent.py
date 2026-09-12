"""Job Agent — a free-text job description in, structured requirements out.

Runs when a recruiter creates or edits a job. The result feeds two things: the
Matching Agent (which compares against structured requirements, not prose) and
the RAG index (which embeds the responsibilities and technologies the agent
pulled out).

The agent may *add* to what the recruiter typed but never removes it — a
recruiter's explicit "Kubernetes required" must survive whatever the model
thinks of the description.
"""
import logging
from typing import List, Tuple

from app.agents import fallback
from app.agents.llm import llm_available, model_label, structured_call
from app.agents.prompts import JOB_SYSTEM, JOB_USER
from app.agents.safety import sanitize_document
from app.schemas.ai import JobAnalysis

logger = logging.getLogger(__name__)


def analyze_job(
    *,
    title: str,
    company: str,
    description: str,
    location: str = "",
    employment_type: str = "",
    experience_required: float | None = None,
    required_skills: List[str] | None = None,
    preferred_skills: List[str] | None = None,
) -> Tuple[JobAnalysis, str]:
    """Return `(analysis, model_label)`."""
    required_skills = required_skills or []
    preferred_skills = preferred_skills or []
    text = sanitize_document(description)

    if not llm_available():
        return (
            fallback.analyze_job(title, text, required_skills, preferred_skills),
            "rule-based-fallback",
        )

    try:
        analysis = structured_call(
            JOB_SYSTEM,
            JOB_USER.format(
                title=title,
                company=company,
                location=location or "not specified",
                employment_type=employment_type or "not specified",
                experience_required=(
                    f"{experience_required} years" if experience_required else "not specified"
                ),
                required_skills=", ".join(required_skills) or "none listed",
                preferred_skills=", ".join(preferred_skills) or "none listed",
                description=text,
            ),
            JobAnalysis,
        )
    except Exception as exc:
        logger.warning("Job agent fell back to rules: %s", exc)
        return (
            fallback.analyze_job(title, text, required_skills, preferred_skills),
            "rule-based-fallback",
        )

    # Re-assert what the human entered. The model is allowed to enrich the
    # requirements, not to overrule the recruiter.
    analysis.required_skills = _merge(required_skills, analysis.required_skills)
    analysis.preferred_skills = _merge(preferred_skills, analysis.preferred_skills)
    if experience_required and not analysis.minimum_years:
        analysis.minimum_years = float(experience_required)
    return analysis, model_label()


def _merge(human: List[str], model: List[str]) -> List[str]:
    """Human entries first, then anything new the model found."""
    seen = set()
    merged: List[str] = []
    for item in list(human) + list(model):
        key = (item or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(item.strip())
    return merged
