"""End-to-end check of the Phase 1 success criteria (spec section 20).

Walks the whole workflow against a running server: register both roles, build a
profile, upload and analyse a resume, post a job, apply, screen with the agent,
and record a human decision. Prints a tick per criterion.

    python smoke_test.py [http://127.0.0.1:8000]
"""
import sys
import uuid

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
API = f"{BASE}/api/v1"

RESUME_TEXT = """John Doe
Senior Backend Engineer | Bengaluru, India | john.doe@example.com

SUMMARY
Backend engineer with 6 years of experience building distributed services in
Node.js and TypeScript. Owned payment and identity services handling 4k req/s.

EXPERIENCE
Senior Backend Engineer, Fintech Corp (2021 - present)
- Designed REST APIs in Node.js and TypeScript serving 4k requests per second
- Migrated the billing service to PostgreSQL and cut p99 latency by 40%
- Ran services on AWS ECS with Docker, Terraform and GitHub Actions CI/CD
- Introduced Redis caching and Kafka event streaming across four services

Backend Engineer, Retail Systems Ltd (2019 - 2021)
- Built microservices in Node.js with Express and MongoDB
- Wrote unit tests with Jest and raised coverage from 20% to 78%

EDUCATION
B.Tech Computer Science, VIT Vellore, 2019

CERTIFICATIONS
AWS Certified Solutions Architect - Associate

PROJECTS
Ledger Service - double-entry accounting service in TypeScript on PostgreSQL
"""

JOB_DESCRIPTION = """We are hiring a Senior Backend Engineer to own our payments platform.

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
"""

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    results.append((label, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail else ""))
    return ok


def build_pdf(text: str) -> bytes:
    """A minimal one-page PDF with a real text layer, written by hand.

    Avoids a reportlab dependency just to produce a fixture. Each line becomes a
    Td-positioned Tj string, which pypdf reads back as ordinary text.
    """
    lines = [line[:95] for line in text.splitlines()]
    parts = ["BT", "/F1 9 Tf", "1 0 0 1 40 780 Tm", "11 TL"]
    for line in lines:
        escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
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


def main() -> int:
    suffix = uuid.uuid4().hex[:8]
    client = httpx.Client(base_url=API, timeout=180.0)

    health = client.get("/health").json()
    check("Server is up", health.get("status") == "ok", health.get("database", ""))

    status = client.get("/ai/status").json()
    print(f"      AI layer: llm={status['llm']} embeddings={status['embeddings']}")

    # --- Auth ---------------------------------------------------------------
    cand = client.post(
        "/auth/register",
        json={
            "email": f"cand.{suffix}@example.com",
            "password": "Passw0rd!23",
            "full_name": "John Doe",
            "role": "CANDIDATE",
        },
    )
    check("Candidate can register/login", cand.status_code == 201, str(cand.status_code))
    cand_headers = {"Authorization": f"Bearer {cand.json()['access_token']}"}

    rec = client.post(
        "/auth/register",
        json={
            "email": f"rec.{suffix}@example.com",
            "password": "Passw0rd!23",
            "full_name": "Riya Recruiter",
            "role": "RECRUITER",
            "company": "Fintech Corp",
        },
    )
    check("Recruiter can register/login", rec.status_code == 201, str(rec.status_code))
    rec_headers = {"Authorization": f"Bearer {rec.json()['access_token']}"}

    # --- RBAC ---------------------------------------------------------------
    forbidden = client.get("/recruiter/metrics", headers=cand_headers)
    check("RBAC blocks a candidate from recruiter routes", forbidden.status_code == 403,
          str(forbidden.status_code))
    forbidden2 = client.get("/candidates/me", headers=rec_headers)
    check("RBAC blocks a recruiter from candidate routes", forbidden2.status_code == 403,
          str(forbidden2.status_code))
    unauth = client.get("/candidates/me")
    check("Unauthenticated requests are rejected", unauth.status_code == 401, str(unauth.status_code))

    # --- Profile ------------------------------------------------------------
    profile = client.put(
        "/candidates/me",
        headers=cand_headers,
        json={
            "phone": "+91 90000 00000",
            "location": "Bengaluru, India",
            "headline": "Senior Backend Engineer",
            "years_experience": 6,
            "skills": ["Node.js", "TypeScript", "PostgreSQL", "AWS"],
            "education": [{"degree": "B.Tech Computer Science", "institution": "VIT", "year": "2019"}],
            "projects": [{"name": "Ledger Service", "description": "Double-entry accounting",
                          "technologies": ["TypeScript", "PostgreSQL"]}],
        },
    )
    check("Candidate can create a profile", profile.status_code == 200, str(profile.status_code))

    # --- Resume -------------------------------------------------------------
    pdf = build_pdf(RESUME_TEXT)
    upload = client.post(
        "/candidates/resume",
        headers=cand_headers,
        files={"file": ("john_doe_resume.pdf", pdf, "application/pdf")},
    )
    ok = upload.status_code == 201
    check("Candidate can upload a resume", ok, str(upload.status_code) if not ok else "")
    if ok:
        body = upload.json()
        check("Resume text was extracted", len(body.get("text_preview") or "") > 200,
              f"{len(body.get('text_preview') or '')} chars")

    analyzed = client.post("/ai/resume/analyze", headers=cand_headers)
    ok = analyzed.status_code == 200
    if ok:
        analysis = analyzed.json().get("ai_analysis") or {}
        check(
            "AI can extract resume information",
            bool(analysis.get("skills") or analysis.get("technologies")),
            f"skills={analysis.get('skills')} tech={analysis.get('technologies')} "
            f"years={analysis.get('experience_years')} model={analyzed.json().get('analysis_model')}",
        )
    else:
        check("AI can extract resume information", False, analyzed.text[:200])

    # --- Job ----------------------------------------------------------------
    job = client.post(
        "/jobs",
        headers=rec_headers,
        json={
            "title": "Senior Backend Engineer",
            "company": "Fintech Corp",
            "location": "Bengaluru, India",
            "employment_type": "Full-time",
            "experience_required": 5,
            "required_skills": ["Node.js", "TypeScript", "PostgreSQL", "AWS"],
            "preferred_skills": ["Kubernetes", "GraphQL"],
            "description": JOB_DESCRIPTION,
        },
    )
    ok = job.status_code == 201
    check("Recruiter can create a job", ok, str(job.status_code) if not ok else "")
    if not ok:
        print(job.text[:400])
        return 1
    job_id = job.json()["id"]
    jd = job.json().get("jd_analysis") or {}
    check("AI can analyse the job description", bool(jd.get("required_skills")),
          f"required={jd.get('required_skills')} min_years={jd.get('minimum_years')}")

    edit = client.put(f"/jobs/{job_id}", headers=rec_headers, json={"location": "Bengaluru / Remote"})
    check("Recruiter can edit a job", edit.status_code == 200, str(edit.status_code))

    # --- Browse and apply ---------------------------------------------------
    jobs = client.get("/jobs", headers=cand_headers)
    check("Candidate can browse jobs", jobs.status_code == 200 and len(jobs.json()) >= 1,
          f"{len(jobs.json())} jobs")

    detail = client.get(f"/jobs/{job_id}", headers=cand_headers)
    check("Candidate can view job details", detail.status_code == 200, str(detail.status_code))

    apply = client.post(f"/jobs/{job_id}/apply", headers=cand_headers,
                        json={"cover_note": "I have shipped exactly this stack for six years."})
    ok = apply.status_code == 201
    check("Candidate can apply", ok, str(apply.status_code) if not ok else "")
    if not ok:
        print(apply.text[:400])
        return 1
    application_id = apply.json()["id"]

    duplicate = client.post(f"/jobs/{job_id}/apply", headers=cand_headers, json={})
    check("Duplicate applications are rejected", duplicate.status_code == 409,
          str(duplicate.status_code))

    recs = client.get("/candidates/recommended-jobs", headers=cand_headers)
    check("RAG recommends jobs to the candidate",
          recs.status_code == 200 and len(recs.json()) >= 1,
          f"top={recs.json()[0]['title']} @ {recs.json()[0]['relevance']}%" if recs.json() else "none")

    apps = client.get(f"/jobs/{job_id}/applications", headers=rec_headers)
    check("Recruiter can see applications", apps.status_code == 200 and len(apps.json()) == 1,
          f"{len(apps.json())} applications")

    # --- Screening ----------------------------------------------------------
    screen = client.post(f"/ai/screen/{application_id}", headers=rec_headers, json={"force": True})
    ok = screen.status_code == 201
    if not ok:
        check("AI can calculate a match score", False, screen.text[:300])
        return 1
    s = screen.json()
    check("RAG retrieves relevant candidate/JD context", len(s["retrieved_context"]) > 0,
          f"{len(s['retrieved_context'])} chunks")
    check("AI can calculate a match score", s["overall_match"] > 0,
          f"overall={s['overall_match']}% skills={s['skills_match']}% exp={s['experience_match']}% "
          f"tech={s['technology_match']}% edu={s['education_match']}% conf={s['confidence']}%")
    check("AI can explain the score", len(s["explanation"]) > 20,
          f"{s['recommendation']} | strengths={len(s['strengths'])} gaps={len(s['skill_gaps'])} "
          f"evidence={len(s['evidence'])}")
    check("Agent workflow is traced (goal/plan/execute/evaluate)",
          any(step["step"] == "plan" for step in s["agent_trace"])
          and any(step["step"] == "evaluate" for step in s["agent_trace"]),
          " -> ".join(step["step"] for step in s["agent_trace"]))

    c360 = client.get(f"/applications/{application_id}/candidate-360", headers=rec_headers)
    check("Recruiter can review the AI recommendation (Candidate 360)",
          c360.status_code == 200 and c360.json()["screening"] is not None,
          str(c360.status_code))

    status_now = client.get(f"/applications/{application_id}", headers=rec_headers).json()["status"]
    check("Screening moves the application to SCREENING, not a final status",
          status_now == "SCREENING", status_now)

    # --- HITL ---------------------------------------------------------------
    bad_reject = client.post(f"/applications/{application_id}/review", headers=rec_headers,
                             json={"decision": "REJECT"})
    check("A rejection without a reason is refused", bad_reject.status_code == 422,
          str(bad_reject.status_code))

    review = client.post(
        f"/applications/{application_id}/review",
        headers=rec_headers,
        json={"decision": "SHORTLIST", "comment": "Strong stack overlap; moving to interview."},
    )
    ok = review.status_code == 201
    check("Recruiter can Shortlist/Hold/Reject", ok, str(review.status_code) if not ok else "")
    if ok:
        r = review.json()
        check("The human decision is stored with the AI's recommendation",
              r["decision"] == "SHORTLIST" and r["ai_recommendation"] is not None,
              f"AI said {r['ai_recommendation']} @ {r['ai_score']}% "
              f"(confidence {r['ai_confidence']}%), human said {r['decision']}, "
              f"override={r['overrode_ai']}")

    final = client.get("/candidates/applications", headers=cand_headers).json()[0]
    check("Candidate can see the application status", final["status"] == "SHORTLISTED",
          final["status"])
    check("The candidate is not shown the recruiter's AI screening",
          final.get("screening") is None and final.get("review") is None)

    metrics = client.get("/recruiter/metrics", headers=rec_headers).json()
    check("Recruiter dashboard metrics are populated",
          metrics["total_jobs"] >= 1 and metrics["total_applications"] >= 1,
          str(metrics))

    queue = client.get("/recruiter/screening-queue", headers=rec_headers).json()
    check("The screening queue excludes decided applications", len(queue) == 0,
          f"{len(queue)} pending")

    # --- Summary ------------------------------------------------------------
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} checks passed")
    failed = [label for label, ok, _ in results if not ok]
    if failed:
        print("Failed: " + "; ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
