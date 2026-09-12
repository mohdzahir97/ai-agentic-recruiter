"""Seed the database with demo accounts, jobs, resumes and applications.

Gives you something to click through immediately: three candidates with real
resume PDFs, three jobs, and six applications spread across the lifecycle —
one already screened and decided, so the HITL history is not empty.

    python seed.py           # add demo data, keeping anything already there
    python seed.py --reset   # delete the database, uploads and vector store first

Every account uses the password below.
"""
import argparse
import shutil
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal, engine, init_db
from app.models import (
    Application,
    ApplicationStatus,
    Candidate,
    Job,
    JobStatus,
    Recruiter,
    User,
    UserRole,
)
from app.services import job_service, resume_service

PASSWORD = "Passw0rd!23"

# --- Demo content ------------------------------------------------------------

RESUMES = {
    "john.doe@example.com": """John Doe
Senior Backend Engineer | Bengaluru, India

SUMMARY
Backend engineer with 6 years of experience building distributed services in
Node.js and TypeScript. Owned payment and identity services at 4k req/s.

EXPERIENCE
Senior Backend Engineer, Fintech Corp (2021 - present)
- Designed REST APIs in Node.js and TypeScript serving 4k requests per second
- Migrated the billing service to PostgreSQL and cut p99 latency by 40%
- Ran services on AWS ECS with Docker, Terraform and GitHub Actions CI/CD
- Introduced Redis caching and Kafka event streaming across four services
- Mentored two junior engineers through their first production launches

Backend Engineer, Retail Systems Ltd (2019 - 2021)
- Built microservices in Node.js with Express and MongoDB
- Raised Jest test coverage from 20% to 78%

EDUCATION
B.Tech Computer Science, VIT Vellore, 2019

CERTIFICATIONS
AWS Certified Solutions Architect - Associate

PROJECTS
Ledger Service - double-entry accounting service in TypeScript on PostgreSQL
""",
    "priya.sharma@example.com": """Priya Sharma
Machine Learning Engineer | Hyderabad, India

SUMMARY
ML engineer with 4 years of experience shipping NLP and retrieval systems.
Built a production RAG assistant serving 800 internal users.

EXPERIENCE
Machine Learning Engineer, DataWorks (2022 - present)
- Built a retrieval-augmented question answering system with LangChain
- Served embeddings from a vector database and tuned chunking for recall
- Deployed FastAPI inference services on GCP with Docker
- Fine-tuned transformer models in PyTorch for document classification

Data Scientist, Analytics Hub (2021 - 2022)
- Built churn models in Python with scikit-learn and pandas
- Automated reporting pipelines against PostgreSQL

EDUCATION
M.Tech Data Science, IIIT Hyderabad, 2021
B.Sc Statistics, Osmania University, 2019

PROJECTS
DocuChat - a document question answering assistant using RAG and LangChain
""",
    "arjun.mehta@example.com": """Arjun Mehta
Frontend Engineer | Pune, India

SUMMARY
Frontend engineer with 3 years of experience building React interfaces.
Focused on design systems and accessible component libraries.

EXPERIENCE
Frontend Engineer, WebScale (2022 - present)
- Built dashboards in React and TypeScript with Tailwind CSS
- Migrated a legacy app to Next.js and cut first-load JS by 45%
- Wrote component tests with Jest and Testing Library

Junior Frontend Developer, Creative Labs (2021 - 2022)
- Built marketing sites in HTML, CSS and JavaScript
- Integrated REST APIs and worked with Git-based review workflows

EDUCATION
BCA, Symbiosis Pune, 2021

PROJECTS
Component Kit - an accessible React component library used by three teams
""",
}

JOBS = [
    {
        "title": "Senior Backend Engineer",
        "company": "Fintech Corp",
        "location": "Bengaluru, India",
        "employment_type": "Full-time",
        "experience_required": 5,
        "required_skills": ["Node.js", "TypeScript", "PostgreSQL", "AWS"],
        "preferred_skills": ["Kubernetes", "GraphQL"],
        "description": """We are hiring a Senior Backend Engineer to own our payments platform.

You will:
- Design and build REST APIs in Node.js and TypeScript
- Model and tune data in PostgreSQL, and use Redis where caching helps
- Deploy and operate services on AWS using Docker and Terraform
- Work with Kafka event streams across service boundaries
- Mentor two engineers and set the standard for testing

Requirements:
- 5+ years of professional backend experience
- Strong Node.js and TypeScript
- Production PostgreSQL and AWS experience
- Bachelor's degree in Computer Science or equivalent experience

Bonus:
- Kubernetes in production
- GraphQL
""",
    },
    {
        "title": "AI / ML Engineer (RAG)",
        "company": "Fintech Corp",
        "location": "Remote, India",
        "employment_type": "Full-time",
        "experience_required": 3,
        "required_skills": ["Python", "LangChain", "RAG", "FastAPI"],
        "preferred_skills": ["PyTorch", "Docker"],
        "description": """We are building an internal AI assistant over our own documents.

You will:
- Build retrieval-augmented generation pipelines with LangChain
- Choose chunking and embedding strategies, and measure retrieval quality
- Serve models behind FastAPI services
- Evaluate output quality and set up guardrails

Requirements:
- 3+ years of Python engineering experience
- Hands-on RAG and vector database experience
- Comfortable with FastAPI and Docker
- Bachelor's degree in a technical field

Bonus:
- PyTorch and model fine-tuning
- Experience running inference on GCP or AWS
""",
    },
    {
        "title": "Frontend Engineer",
        "company": "Fintech Corp",
        "location": "Pune, India",
        "employment_type": "Full-time",
        "experience_required": 2,
        "required_skills": ["React", "TypeScript", "Next.js", "Tailwind CSS"],
        "preferred_skills": ["Testing", "Accessibility"],
        "description": """We need a Frontend Engineer for our customer-facing dashboards.

You will:
- Build interfaces in React, Next.js and TypeScript
- Style with Tailwind CSS against a shared design system
- Write component tests and keep bundles small
- Work closely with backend engineers on API design

Requirements:
- 2+ years of professional frontend experience
- Strong React and TypeScript
- Experience with Next.js
""",
    },
]


def build_pdf(text: str) -> bytes:
    """Hand-rolled single-page PDF with a real text layer.

    Keeps the seed dependency-free while still producing files the normal
    upload path (pypdf extraction included) can process for real.
    """
    parts = ["BT", "/F1 9 Tf", "1 0 0 1 40 780 Tm", "11 TL"]
    for line in text.splitlines():
        escaped = line[:95].replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        parts.append(f"({escaped}) Tj T*")
    parts.append("ET")
    stream = "\n".join(parts).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


def reset() -> None:
    settings = get_settings()
    engine.dispose()
    if settings.database_url.startswith("sqlite"):
        db_file = settings.database_url.split("///", 1)[-1]
        path = Path(db_file)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent / path
        path.unlink(missing_ok=True)
        print(f"Deleted {path}")
    else:
        from app.db.base import Base

        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables")

    for directory in (settings.upload_path, settings.chroma_path):
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)
            print(f"Deleted {directory}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset", action="store_true", help="delete existing data before seeding"
    )
    args = parser.parse_args()

    if args.reset:
        reset()

    init_db()
    db = SessionLocal()

    try:
        if db.scalar(select(User).where(User.email == "riya.recruiter@example.com")):
            print("Demo data already present. Re-run with --reset to rebuild it.")
            return 0

        # --- Recruiter -------------------------------------------------------
        recruiter_user = User(
            email="riya.recruiter@example.com",
            password_hash=hash_password(PASSWORD),
            full_name="Riya Recruiter",
            role=UserRole.RECRUITER.value,
        )
        db.add(recruiter_user)
        db.flush()
        recruiter = Recruiter(
            user_id=recruiter_user.id, company="Fintech Corp", title="Talent Partner"
        )
        db.add(recruiter)
        db.flush()

        # --- Candidates ------------------------------------------------------
        candidate_specs = [
            ("john.doe@example.com", "John Doe", "Bengaluru, India",
             "Senior Backend Engineer", 6.0,
             ["Node.js", "TypeScript", "PostgreSQL", "AWS", "Docker", "Kafka"]),
            ("priya.sharma@example.com", "Priya Sharma", "Hyderabad, India",
             "Machine Learning Engineer", 4.0,
             ["Python", "LangChain", "RAG", "FastAPI", "PyTorch", "Docker"]),
            ("arjun.mehta@example.com", "Arjun Mehta", "Pune, India",
             "Frontend Engineer", 3.0,
             ["React", "TypeScript", "Next.js", "Tailwind CSS", "Testing"]),
        ]

        candidates = []
        for email, name, location, headline, years, skills in candidate_specs:
            user = User(
                email=email,
                password_hash=hash_password(PASSWORD),
                full_name=name,
                role=UserRole.CANDIDATE.value,
            )
            db.add(user)
            db.flush()
            candidate = Candidate(
                user_id=user.id,
                location=location,
                headline=headline,
                years_experience=years,
                phone="+91 90000 00000",
                skills=skills,
                education=[],
                projects=[],
            )
            db.add(candidate)
            db.flush()
            candidates.append(candidate)

        db.commit()

        # --- Resumes ---------------------------------------------------------
        # Written through the real upload path so extraction, storage and
        # indexing behave exactly as they do for a user.
        for candidate in candidates:
            text = RESUMES[candidate.user.email]
            resume_service.upload(
                db,
                candidate,
                filename=f"{candidate.user.full_name.lower().replace(' ', '_')}_resume.pdf",
                content=build_pdf(text),
                content_type="application/pdf",
            )
            resume_service.analyze(db, candidate)
            print(f"Seeded resume for {candidate.user.full_name}")

        # --- Jobs ------------------------------------------------------------
        jobs = []
        for spec in JOBS:
            job = Job(recruiter_id=recruiter.id, status=JobStatus.ACTIVE.value, **spec)
            db.add(job)
            db.flush()
            jobs.append(job)
        db.commit()

        for job in jobs:
            job_service.run_job_agent(db, job)
            print(f"Seeded job: {job.title}")

        # --- Applications ----------------------------------------------------
        # Deliberately crossed over: the backend engineer also applies to the
        # ML role, so the screening queue has an obvious weak match in it.
        pairs = [
            (candidates[0], jobs[0]),
            (candidates[0], jobs[1]),
            (candidates[1], jobs[1]),
            (candidates[1], jobs[0]),
            (candidates[2], jobs[2]),
            (candidates[2], jobs[0]),
        ]
        for candidate, job in pairs:
            db.add(
                Application(
                    job_id=job.id,
                    candidate_id=candidate.id,
                    status=ApplicationStatus.APPLIED.value,
                    cover_note=f"I am interested in the {job.title} role.",
                )
            )
        db.commit()

        print(
            f"\nSeeded 1 recruiter, {len(candidates)} candidates, {len(jobs)} jobs "
            f"and {len(pairs)} applications."
        )
        print("\nSign in with any of these - password: " + PASSWORD)
        print("  Recruiter: riya.recruiter@example.com")
        for email, name, *_ in candidate_specs:
            print(f"  Candidate: {email}  ({name})")
        print(
            "\nNothing has been screened yet: open the recruiter's AI Screening "
            "queue and run one to see the full agent workflow."
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
