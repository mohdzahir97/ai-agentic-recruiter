"""Matching Agent — candidate + job + retrieved context in, scored match out.

This is the only agent that reasons rather than extracts, and it is the one
whose output a human acts on. Three things make it safe to show a recruiter:

* it is given retrieved evidence, not the whole documents, so it has something
  specific to quote;
* its output is a validated `MatchResult`, so the UI never parses prose;
* every result passes through `safety.scan_output()` before it is stored.

It produces a recommendation. It never changes an application's status — only
a `HitlReview` does that.
"""
import json
import logging
from typing import Dict, List, Tuple

from app.agents import fallback
from app.agents.llm import llm_available, model_label, structured_call
from app.agents.prompts import MATCH_SYSTEM, MATCH_USER
from app.agents.safety import scan_output
from app.rag.retriever import format_context
from app.schemas.ai import JobAnalysis, MatchResult, ResumeAnalysis

logger = logging.getLogger(__name__)


def match_candidate_to_job(
    resume_analysis: ResumeAnalysis,
    job_analysis: JobAnalysis,
    candidate_chunks: List[Dict],
    job_chunks: List[Dict],
) -> Tuple[MatchResult, str, List[str]]:
    """Return `(result, model_label, safety_notes)`."""
    # The retriever's own similarity is a useful prior for `semantic_match`,
    # and it is the only score here the rule-based path could not produce alone.
    semantic_prior = max((chunk["score"] for chunk in candidate_chunks), default=0.0)

    if not llm_available():
        result = fallback.match(resume_analysis, job_analysis, semantic_prior)
        return result, "rule-based-fallback", ["No LLM configured; keyword matching was used."]

    try:
        result = structured_call(
            MATCH_SYSTEM,
            MATCH_USER.format(
                job_analysis=_pretty(job_analysis),
                resume_analysis=_pretty(resume_analysis),
                candidate_context=format_context(candidate_chunks, "candidate"),
                job_context=format_context(job_chunks, "job"),
            ),
            MatchResult,
        )
    except Exception as exc:
        logger.warning("Matching agent fell back to rules: %s", exc)
        result = fallback.match(resume_analysis, job_analysis, semantic_prior)
        note = f"LLM matching failed ({exc.__class__.__name__}); keyword matching was used."
        return result, "rule-based-fallback", [note]

    safety_notes = scan_output(result)

    if not result.semantic_match and semantic_prior:
        result.semantic_match = round(semantic_prior * 100, 1)
    if not result.overall_match:
        result.overall_match = _weighted_overall(result)
    # Thin evidence must not produce a confident answer, whatever the model says.
    if not candidate_chunks:
        result.confidence = min(result.confidence, 35.0)
        safety_notes.append("No candidate context was retrieved; confidence was capped at 35%.")

    return result, model_label(), safety_notes


def _weighted_overall(result: MatchResult) -> float:
    """Fill in `overall_match` when the model left it at zero."""
    return round(
        0.35 * result.skills_match
        + 0.20 * result.experience_match
        + 0.20 * result.technology_match
        + 0.10 * result.education_match
        + 0.15 * result.semantic_match,
        1,
    )


def _pretty(model) -> str:
    return json.dumps(model.model_dump(mode="json"), indent=2, ensure_ascii=False)
