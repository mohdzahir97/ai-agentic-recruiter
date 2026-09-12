"""The retrieval half of the RAG pipeline.

`vector_store` knows how to store and search; this module knows *what* to
store and search for. It is the only place that turns database rows into the
document text that gets embedded, which keeps that decision in one file.
"""
import logging
from typing import Dict, List

from app.core.config import get_settings
from app.rag import vector_store
from app.rag.vector_store import CANDIDATE_COLLECTION, JOB_COLLECTION

logger = logging.getLogger(__name__)


# --- Document construction ---------------------------------------------------


def candidate_profile_text(candidate, user) -> str:
    """Flatten the structured profile into prose the embedder can use.

    Embeddings are computed over natural language, so `["Node.js","AWS"]` is
    worth writing out as a sentence rather than dumping as JSON.
    """
    parts = [f"Candidate: {user.full_name}"]
    if candidate.headline:
        parts.append(f"Headline: {candidate.headline}")
    if candidate.location:
        parts.append(f"Location: {candidate.location}")
    if candidate.years_experience is not None:
        parts.append(f"Total professional experience: {candidate.years_experience} years")
    if candidate.skills:
        parts.append("Skills: " + ", ".join(candidate.skills))
    for item in candidate.education or []:
        degree = item.get("degree", "") if isinstance(item, dict) else str(item)
        institution = item.get("institution", "") if isinstance(item, dict) else ""
        parts.append(f"Education: {degree} {institution}".strip())
    for item in candidate.projects or []:
        if isinstance(item, dict):
            tech = ", ".join(item.get("technologies", []) or [])
            parts.append(
                f"Project: {item.get('name', '')}. {item.get('description', '')}"
                + (f" Technologies: {tech}." if tech else "")
            )
        else:
            parts.append(f"Project: {item}")
    return "\n".join(p for p in parts if p.strip())


def job_text(job) -> str:
    parts = [
        f"Job title: {job.title}",
        f"Company: {job.company}",
    ]
    if job.location:
        parts.append(f"Location: {job.location}")
    if job.employment_type:
        parts.append(f"Employment type: {job.employment_type}")
    if job.experience_required is not None:
        parts.append(f"Experience required: {job.experience_required} years")
    if job.required_skills:
        parts.append("Required skills: " + ", ".join(job.required_skills))
    if job.preferred_skills:
        parts.append("Preferred skills: " + ", ".join(job.preferred_skills))
    parts.append("Job description:\n" + (job.description or ""))

    analysis = job.jd_analysis or {}
    if analysis.get("responsibilities"):
        parts.append("Responsibilities: " + "; ".join(analysis["responsibilities"]))
    if analysis.get("technologies"):
        parts.append("Technologies: " + ", ".join(analysis["technologies"]))
    if analysis.get("education_requirement"):
        parts.append("Education requirement: " + analysis["education_requirement"])
    return "\n".join(parts)


# --- Indexing ----------------------------------------------------------------


def index_candidate(candidate, user, resume_text: str = "") -> int:
    documents = [{"source": "profile", "text": candidate_profile_text(candidate, user)}]
    if resume_text:
        documents.append({"source": "resume", "text": resume_text})
    return vector_store.index_documents(
        CANDIDATE_COLLECTION, "candidate_id", candidate.id, documents
    )


def index_job(job) -> int:
    return vector_store.index_documents(
        JOB_COLLECTION, "job_id", job.id, [{"source": "job", "text": job_text(job)}]
    )


# --- Retrieval ---------------------------------------------------------------


def retrieve_candidate_context(candidate_id: int, job_query: str, top_k: int = 0) -> List[Dict]:
    """Chunks of *this* candidate that best answer *this* job's requirements."""
    settings = get_settings()
    return vector_store.query(
        CANDIDATE_COLLECTION,
        query_text=job_query,
        top_k=top_k or settings.retrieval_top_k,
        where={"candidate_id": candidate_id},
    )


def retrieve_job_context(job_id: int, candidate_query: str, top_k: int = 0) -> List[Dict]:
    """Chunks of *this* job that best match what the candidate brings."""
    settings = get_settings()
    return vector_store.query(
        JOB_COLLECTION,
        query_text=candidate_query,
        top_k=top_k or settings.retrieval_top_k,
        where={"job_id": job_id},
    )


def recommend_jobs(candidate_query: str, top_k: int = 10) -> List[Dict]:
    """Semantic job search across every indexed job, for the candidate portal."""
    hits = vector_store.query(JOB_COLLECTION, query_text=candidate_query, top_k=top_k)
    # One job produces several chunks; keep each job once, at its best score.
    best: Dict[int, Dict] = {}
    for hit in hits:
        job_id = hit["metadata"].get("job_id")
        if job_id is None:
            continue
        if job_id not in best or hit["score"] > best[job_id]["score"]:
            best[job_id] = hit
    return sorted(best.values(), key=lambda h: h["score"], reverse=True)


def format_context(chunks: List[Dict], label: str) -> str:
    """Render retrieved chunks for a prompt, numbered so the model can cite them."""
    if not chunks:
        return f"[No {label} context retrieved]"
    lines = []
    for index, chunk in enumerate(chunks, start=1):
        lines.append(f"[{label} {index} | source={chunk['source']} | score={chunk['score']}]")
        lines.append(chunk["text"])
    return "\n".join(lines)
