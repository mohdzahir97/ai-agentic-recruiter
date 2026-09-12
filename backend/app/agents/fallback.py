"""Deterministic, no-LLM implementations of the three agents.

Used automatically when no API key is configured (`llm_available()` is False)
and whenever a live call fails, so the application never dead-ends on a
missing key or a rate limit. It is keyword matching, not understanding — the
results are labelled `rule-based-fallback` everywhere they surface, and the
confidence it reports is deliberately low.

Keeping it here also gives the LLM path something to be compared against,
which is the honest way to show what the model is actually adding.
"""
import re
from typing import Dict, List, Set

from app.models.enums import Recommendation
from app.schemas.ai import Evidence, JobAnalysis, MatchResult, ResumeAnalysis

# A small, readable vocabulary. Canonical name -> spellings seen in the wild.
SKILL_VOCABULARY: Dict[str, List[str]] = {
    "Python": ["python"],
    "JavaScript": ["javascript", "java script", "es6"],
    "TypeScript": ["typescript"],
    "Java": ["java"],
    "Go": ["golang", "go lang"],
    "C#": ["c#", "csharp", ".net"],
    "Node.js": ["node.js", "nodejs", "node js"],
    "React": ["react", "react.js", "reactjs"],
    "Next.js": ["next.js", "nextjs"],
    "Angular": ["angular"],
    "Vue": ["vue.js", "vuejs", "vue"],
    "FastAPI": ["fastapi", "fast api"],
    "Django": ["django"],
    "Flask": ["flask"],
    "Spring Boot": ["spring boot", "springboot"],
    "Express": ["express.js", "expressjs", "express"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "Elasticsearch": ["elasticsearch", "elastic search"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Terraform": ["terraform"],
    "CI/CD": ["ci/cd", "cicd", "continuous integration", "jenkins", "github actions"],
    "Kafka": ["kafka"],
    "RabbitMQ": ["rabbitmq"],
    "GraphQL": ["graphql"],
    "REST API": ["rest api", "restful", "rest apis"],
    "Microservices": ["microservice", "microservices"],
    "SQL": ["sql"],
    "Git": ["git", "github", "gitlab"],
    "Linux": ["linux", "unix"],
    "Machine Learning": ["machine learning", "scikit", "sklearn"],
    "Deep Learning": ["deep learning", "pytorch", "tensorflow"],
    "LangChain": ["langchain"],
    "RAG": ["retrieval augmented", "retrieval-augmented"],
    "Pandas": ["pandas"],
    "Tailwind CSS": ["tailwind"],
    "HTML/CSS": ["html", "css"],
    "Agile": ["agile", "scrum"],
    "Testing": ["pytest", "jest", "unit test", "unit testing", "tdd"],
}

# Which of the above count as "technologies" for the technology-match score.
TECHNOLOGY_NAMES = {
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Kafka", "RabbitMQ",
    "Redis", "PostgreSQL", "MySQL", "MongoDB", "Elasticsearch", "GraphQL", "CI/CD",
    "Git", "Linux", "LangChain", "Deep Learning",
}

_DEGREE = re.compile(
    r"\b(b\.?tech|b\.?e\.?|b\.?sc|bca|bachelors?|m\.?tech|m\.?sc|mca|masters?|mba|ph\.?d|doctorate)\b",
    re.IGNORECASE,
)
_YEARS = re.compile(r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE)
_CERT = re.compile(
    r"\b((?:aws|azure|google|gcp|oracle|cisco|scrum|pmp|kubernetes|cka)[^\n,;.]{0,60}"
    r"(?:certified|certification|certificate)[^\n,;.]{0,40})",
    re.IGNORECASE,
)


def find_skills(text: str) -> List[str]:
    """Canonical skill names mentioned anywhere in `text`."""
    lowered = f" {(text or '').lower()} "
    found = []
    for canonical, spellings in SKILL_VOCABULARY.items():
        if any(spelling in lowered for spelling in spellings):
            found.append(canonical)
    return found


def _max_years(text: str) -> float:
    matches = _YEARS.findall(text or "")
    return max((float(m) for m in matches), default=0.0)


def analyze_resume(text: str) -> ResumeAnalysis:
    skills = find_skills(text)
    education = sorted({
        _tidy_line(line)
        for line in (text or "").splitlines()
        if _DEGREE.search(line)
    })
    certifications = sorted({_tidy_line(m) for m in _CERT.findall(text or "")})
    return ResumeAnalysis(
        skills=[s for s in skills if s not in TECHNOLOGY_NAMES],
        technologies=[s for s in skills if s in TECHNOLOGY_NAMES],
        experience_years=_max_years(text),
        education=education[:5],
        projects=[],
        certifications=certifications[:5],
        summary="Extracted without an LLM: keyword matching over the resume text.",
    )


def analyze_job(
    title: str, description: str, required: List[str], preferred: List[str]
) -> JobAnalysis:
    combined = f"{title}\n{description}"
    detected = find_skills(combined)
    minimum_years = _max_years(description)
    return JobAnalysis(
        required_skills=_dedupe(
            list(required) + [s for s in detected if s not in TECHNOLOGY_NAMES]
        ),
        preferred_skills=_dedupe(preferred),
        technologies=_dedupe([s for s in detected if s in TECHNOLOGY_NAMES]),
        experience_requirement=f"{minimum_years:g}+ years" if minimum_years else "",
        minimum_years=minimum_years,
        education_requirement="Bachelor's degree" if _DEGREE.search(description or "") else "",
        responsibilities=[
            _tidy_line(line)
            for line in (description or "").splitlines()
            if line.strip().startswith(("-", "*")) and len(line.strip()) > 8
        ][:8],
        seniority=_seniority(title, minimum_years),
    )


def match(resume: ResumeAnalysis, job: JobAnalysis, semantic_score: float = 0.0) -> MatchResult:
    """Set-overlap scoring. Transparent, and useless at synonyms — by design."""
    candidate_all = _norm(resume.skills) | _norm(resume.technologies)
    required = _norm(job.required_skills)
    preferred = _norm(job.preferred_skills)
    technologies = _norm(job.technologies)

    skills_match = _overlap(required, candidate_all)
    # Preferred skills lift the score but never sink it, so a candidate is not
    # punished for missing a nice-to-have.
    if preferred:
        skills_match = min(100.0, skills_match + 0.25 * _overlap(preferred, candidate_all))
    technology_match = _overlap(technologies, candidate_all) if technologies else skills_match

    if job.minimum_years <= 0:
        experience_match = 75.0
    else:
        experience_match = min(100.0, round(resume.experience_years / job.minimum_years * 100, 1))

    education_match = 80.0 if resume.education else 50.0
    if job.education_requirement and not resume.education:
        education_match = 40.0

    semantic = round(max(0.0, min(100.0, semantic_score * 100)), 1)

    overall = round(
        0.35 * skills_match
        + 0.20 * experience_match
        + 0.20 * technology_match
        + 0.10 * education_match
        + 0.15 * (semantic or skills_match),
        1,
    )

    matched = sorted(_display(required & candidate_all, job))
    missing = sorted(_display(required - candidate_all, job))

    return MatchResult(
        skills_match=skills_match,
        experience_match=experience_match,
        technology_match=technology_match,
        education_match=education_match,
        semantic_match=semantic,
        overall_match=overall,
        # Low on purpose: keyword overlap cannot tell depth from a mention, and
        # a recruiter should weigh it accordingly.
        confidence=45.0,
        recommendation=recommendation_for(overall),
        strengths=[f"{skill} found in the candidate's documents" for skill in matched[:6]],
        skill_gaps=[f"{skill} not found in the candidate's documents" for skill in missing[:6]],
        explanation=(
            f"Rule-based match (no LLM configured). {len(matched)} of {len(required)} required "
            f"skills were found by keyword search"
            + (f"; missing: {', '.join(missing[:5])}." if missing else ".")
            + " Treat this as a rough filter, not an assessment."
        ),
        evidence=[
            Evidence(
                claim=f"{skill} appears in the candidate's documents",
                source="resume",
                quote=skill,
            )
            for skill in matched[:5]
        ],
    )


def recommendation_for(overall: float) -> Recommendation:
    """The one place score-to-label thresholds are defined."""
    if overall >= 85:
        return Recommendation.STRONG_MATCH
    if overall >= 70:
        return Recommendation.GOOD_MATCH
    if overall >= 50:
        return Recommendation.PARTIAL_MATCH
    return Recommendation.WEAK_MATCH


# --- helpers -----------------------------------------------------------------


def _norm(items: List[str]) -> Set[str]:
    return {item.strip().lower() for item in items or [] if item and item.strip()}


def _overlap(needed: Set[str], have: Set[str]) -> float:
    if not needed:
        return 70.0  # nothing specified — neither credit nor penalty
    return round(len(needed & have) / len(needed) * 100, 1)


def _display(normalised: Set[str], job: JobAnalysis) -> List[str]:
    """Map lower-cased names back to the job's original capitalisation."""
    lookup = {s.lower(): s for s in (job.required_skills or []) + (job.technologies or [])}
    return [lookup.get(item, item) for item in normalised]


def _dedupe(items: List[str]) -> List[str]:
    seen, out = set(), []
    for item in items or []:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _tidy_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip(" -*\t")[:160]


def _seniority(title: str, years: float) -> str:
    lowered = (title or "").lower()
    if any(word in lowered for word in ("senior", "sr.", "lead", "principal", "staff")):
        return "Senior"
    if any(word in lowered for word in ("junior", "jr.", "intern", "graduate", "entry")):
        return "Junior"
    if years >= 7:
        return "Senior"
    if years >= 3:
        return "Mid"
    return "Junior" if years else ""
