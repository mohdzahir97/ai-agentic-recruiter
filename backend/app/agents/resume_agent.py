"""Resume Agent — resume text in, structured `ResumeAnalysis` out.

    Resume PDF -> text extraction -> Resume Agent -> structured profile

The agent never returns prose. If the LLM cannot produce a valid
`ResumeAnalysis`, the rule-based extractor runs instead and the result is
labelled as such, so a screening never silently rests on nothing.
"""
import logging
from typing import Tuple

from app.agents import fallback
from app.agents.llm import llm_available, model_label, structured_call
from app.agents.prompts import RESUME_SYSTEM, RESUME_USER
from app.agents.safety import sanitize_document
from app.schemas.ai import ResumeAnalysis

logger = logging.getLogger(__name__)


def analyze_resume(resume_text: str) -> Tuple[ResumeAnalysis, str]:
    """Return `(analysis, model_label)`."""
    text = sanitize_document(resume_text)
    if not text:
        return ResumeAnalysis(), "empty-input"

    if not llm_available():
        return fallback.analyze_resume(text), "rule-based-fallback"

    try:
        analysis = structured_call(
            RESUME_SYSTEM, RESUME_USER.format(resume_text=text), ResumeAnalysis
        )
    except Exception as exc:
        logger.warning("Resume agent fell back to rules: %s", exc)
        return fallback.analyze_resume(text), "rule-based-fallback"

    # A model that returns nothing at all is worse than keyword matching, so
    # take the rule-based result in that case rather than storing an empty one.
    if not analysis.skills and not analysis.technologies:
        rules = fallback.analyze_resume(text)
        if rules.skills or rules.technologies:
            logger.info("Resume agent returned no skills; using the rule-based result")
            return rules, "rule-based-fallback"

    return analysis, model_label()
