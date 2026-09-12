"""Screening workflow, orchestrated with LangGraph.

    Goal -> Plan -> Execute -> Evaluate -> Result

The executing steps are the ones spec section 8 lists:

    analyse job -> retrieve candidate context -> analyse resume
                -> compare -> score -> explain -> evaluate

One linear graph with a single conditional edge (`evaluate` may loop back to
`retrieve` once when the evidence was too thin). No multi-agent choreography —
Phase 1 is about seeing the pattern clearly.

Why a graph at all, when this could be seven function calls? Because the state
object gives every step the same explicit input and output, and because each
step appends to `trace`, which is stored with the screening and rendered in the
UI. The recruiter can see what the agent did, not just what it concluded.
"""
import logging
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents import job_agent, matching_agent, resume_agent
from app.rag import retriever
from app.schemas.ai import JobAnalysis, MatchResult, ResumeAnalysis

logger = logging.getLogger(__name__)

# Confidence below this, on the first pass, is treated as "not enough evidence"
# and triggers one wider retrieval before the agent commits to an answer.
LOW_CONFIDENCE_THRESHOLD = 45.0
MAX_RETRIES = 1


def _append(existing: List[Any], new: List[Any]) -> List[Any]:
    """Reducer so every node can add to `trace` without overwriting it."""
    return (existing or []) + (new or [])


class ScreeningState(TypedDict, total=False):
    # --- Goal (set by the caller) -------------------------------------------
    goal: str
    candidate_id: int
    job_id: int
    resume_text: str
    profile_text: str
    job_payload: Dict[str, Any]
    stored_resume_analysis: Optional[Dict[str, Any]]
    stored_job_analysis: Optional[Dict[str, Any]]

    # --- Working state ------------------------------------------------------
    plan: List[str]
    job_analysis: Optional[JobAnalysis]
    resume_analysis: Optional[ResumeAnalysis]
    candidate_chunks: List[Dict[str, Any]]
    job_chunks: List[Dict[str, Any]]
    top_k: int
    attempt: int

    # --- Result -------------------------------------------------------------
    match: Optional[MatchResult]
    model_used: str
    safety_notes: List[str]
    trace: Annotated[List[Dict[str, Any]], _append]


def _step(name: str, detail: str, **extra) -> Dict[str, Any]:
    return {"step": name, "detail": detail, **extra}


# --- Nodes -------------------------------------------------------------------


def plan_node(state: ScreeningState) -> Dict[str, Any]:
    """Write the plan down before executing it, and keep it in the trace."""
    plan = [
        "Analyse the job description into structured requirements",
        "Retrieve the candidate context most relevant to those requirements",
        "Analyse the resume into a structured candidate profile",
        "Compare the candidate against the job and score each dimension",
        "Generate an explanation, strengths, gaps and evidence",
        "Evaluate the result; retrieve more context and retry once if the evidence is thin",
    ]
    return {
        "plan": plan,
        "attempt": 0,
        "trace": [_step("plan", f"Goal: {state.get('goal', 'screen candidate')}", plan=plan)],
    }


def analyze_job_node(state: ScreeningState) -> Dict[str, Any]:
    """Reuse the stored JD analysis when the Job Agent already ran at creation."""
    stored = state.get("stored_job_analysis")
    if stored:
        return {
            "job_analysis": JobAnalysis.model_validate(stored),
            "trace": [_step("analyze_job", "Reused the stored job analysis")],
        }

    payload = state.get("job_payload") or {}
    analysis, model = job_agent.analyze_job(
        title=payload.get("title", ""),
        company=payload.get("company", ""),
        description=payload.get("description", ""),
        location=payload.get("location", ""),
        employment_type=payload.get("employment_type", ""),
        experience_required=payload.get("experience_required"),
        required_skills=payload.get("required_skills"),
        preferred_skills=payload.get("preferred_skills"),
    )
    return {
        "job_analysis": analysis,
        "trace": [
            _step(
                "analyze_job",
                f"Extracted {len(analysis.required_skills)} required skills",
                model=model,
            )
        ],
    }


def retrieve_node(state: ScreeningState) -> Dict[str, Any]:
    """The RAG step: pull the passages each side needs to be judged on."""
    job_analysis = state.get("job_analysis")
    job_query = _job_query(state, job_analysis)
    top_k = state.get("top_k") or 0

    candidate_chunks = retriever.retrieve_candidate_context(
        state["candidate_id"], job_query, top_k=top_k
    )
    job_chunks = retriever.retrieve_job_context(
        state["job_id"], state.get("profile_text", "") or job_query, top_k=top_k
    )
    return {
        "candidate_chunks": candidate_chunks,
        "job_chunks": job_chunks,
        "trace": [
            _step(
                "retrieve_context",
                f"Retrieved {len(candidate_chunks)} candidate and {len(job_chunks)} job chunks",
                top_score=max((c["score"] for c in candidate_chunks), default=0.0),
            )
        ],
    }


def analyze_resume_node(state: ScreeningState) -> Dict[str, Any]:
    """Reuse the stored resume analysis when the candidate already ran it."""
    stored = state.get("stored_resume_analysis")
    if stored:
        return {
            "resume_analysis": ResumeAnalysis.model_validate(stored),
            "trace": [_step("analyze_resume", "Reused the stored resume analysis")],
        }

    analysis, model = resume_agent.analyze_resume(
        state.get("resume_text") or state.get("profile_text", "")
    )
    return {
        "resume_analysis": analysis,
        "trace": [
            _step(
                "analyze_resume",
                f"Extracted {len(analysis.skills)} skills and "
                f"{len(analysis.technologies)} technologies",
                model=model,
            )
        ],
    }


def compare_node(state: ScreeningState) -> Dict[str, Any]:
    """Compare, score and explain — one call, because they are one judgement."""
    result, model, safety_notes = matching_agent.match_candidate_to_job(
        state.get("resume_analysis") or ResumeAnalysis(),
        state.get("job_analysis") or JobAnalysis(),
        state.get("candidate_chunks") or [],
        state.get("job_chunks") or [],
    )
    trace = [
        _step(
            "compare_and_score",
            f"Overall {result.overall_match}% at {result.confidence}% confidence",
            model=model,
            recommendation=result.recommendation.value,
        ),
        _step(
            "generate_explanation",
            f"{len(result.strengths)} strengths, {len(result.skill_gaps)} gaps, "
            f"{len(result.evidence)} pieces of evidence",
        ),
    ]
    if safety_notes:
        trace.append(_step("safety_check", "; ".join(safety_notes)))
    return {
        "match": result,
        "model_used": model,
        "safety_notes": safety_notes,
        "trace": trace,
    }


def evaluate_node(state: ScreeningState) -> Dict[str, Any]:
    """Judge the agent's own output before it is handed to a human."""
    result = state.get("match")
    attempt = state.get("attempt", 0)
    confidence = result.confidence if result else 0.0
    retrying = _should_retry(state)

    if retrying:
        detail = (
            f"Confidence {confidence}% is below {LOW_CONFIDENCE_THRESHOLD}% — "
            "widening retrieval and re-running the comparison"
        )
    else:
        detail = f"Accepted: {confidence}% confidence over {len(state.get('candidate_chunks') or [])} chunks"

    return {
        "attempt": attempt + 1,
        # A second pass looks at more of the candidate's document rather than
        # asking the same question again — more evidence, not more insistence.
        "top_k": (state.get("top_k") or 0) * 2 or 8,
        "trace": [_step("evaluate", detail, attempt=attempt + 1, retrying=retrying)],
    }


def _should_retry(state: ScreeningState) -> bool:
    result = state.get("match")
    if result is None:
        return False
    if state.get("attempt", 0) >= MAX_RETRIES:
        return False
    # Retrying only helps if there is more to retrieve; with zero chunks the
    # candidate simply has no indexed documents and a wider search finds none.
    if not state.get("candidate_chunks"):
        return False
    return result.confidence < LOW_CONFIDENCE_THRESHOLD


def _route_after_evaluate(state: ScreeningState) -> str:
    # `evaluate_node` has already incremented `attempt`, so re-check against
    # the updated state rather than trusting the flag it wrote into the trace.
    return "retrieve_context" if _should_retry(state) else END


def _job_query(state: ScreeningState, job_analysis: Optional[JobAnalysis]) -> str:
    """What we search the candidate's documents *with*.

    The structured requirements make a better query than the raw posting: the
    boilerplate ("we are a fast-growing team") matches everything and therefore
    discriminates nothing.
    """
    if job_analysis:
        parts = [
            "Required skills: " + ", ".join(job_analysis.required_skills),
            "Technologies: " + ", ".join(job_analysis.technologies),
            "Experience: " + job_analysis.experience_requirement,
            "Responsibilities: " + "; ".join(job_analysis.responsibilities[:5]),
        ]
        query = "\n".join(part for part in parts if part.split(": ", 1)[-1].strip())
        if query.strip():
            return query
    payload = state.get("job_payload") or {}
    return f"{payload.get('title', '')}\n{payload.get('description', '')}"


# --- Graph -------------------------------------------------------------------


def build_graph():
    graph = StateGraph(ScreeningState)
    graph.add_node("plan", plan_node)
    graph.add_node("analyze_job", analyze_job_node)
    graph.add_node("retrieve_context", retrieve_node)
    graph.add_node("analyze_resume", analyze_resume_node)
    graph.add_node("compare_and_score", compare_node)
    graph.add_node("evaluate", evaluate_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "analyze_job")
    graph.add_edge("analyze_job", "retrieve_context")
    graph.add_edge("retrieve_context", "analyze_resume")
    graph.add_edge("analyze_resume", "compare_and_score")
    graph.add_edge("compare_and_score", "evaluate")
    graph.add_conditional_edges(
        "evaluate", _route_after_evaluate, {"retrieve_context": "retrieve_context", END: END}
    )
    return graph.compile()


_compiled = None


def get_screening_graph():
    """Compile once; compiling on every screening is pure overhead."""
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


def run_screening(initial_state: ScreeningState) -> ScreeningState:
    state = dict(initial_state)
    state.setdefault("goal", "Screen this candidate against this job and recommend an action")
    state.setdefault("trace", [])
    return get_screening_graph().invoke(state)
