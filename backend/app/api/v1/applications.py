"""Application detail, the Candidate 360 view, and the HITL review endpoint."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_recruiter
from app.db.session import get_db
from app.models import Recruiter, User
from app.repositories import resume_repo
from app.schemas.application import (
    ApplicationOut,
    Candidate360,
    ReviewOut,
    ReviewRequest,
)
from app.services import application_service, candidate_service, hitl_service, resume_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int,
    recruiter: Recruiter = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    application = application_service.get_for_recruiter(db, recruiter, application_id)
    return application_service.to_out(application)


@router.get("/{application_id}/candidate-360", response_model=Candidate360)
def candidate_360(
    application_id: int,
    recruiter: Recruiter = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> Candidate360:
    """Everything the screening page renders, in one request.

    The page shows profile, resume, AI analysis, match breakdown and decision
    history together; fetching them separately would mean six round-trips and a
    screen that fills in piecemeal.
    """
    application = application_service.get_for_recruiter(db, recruiter, application_id)
    candidate = application.candidate
    resume = resume_repo.latest_for_candidate(db, candidate.id)
    screening = application.latest_screening

    return Candidate360(
        application=application_service.to_out(application),
        job={
            "id": application.job.id,
            "title": application.job.title,
            "company": application.job.company,
            "location": application.job.location,
            "employment_type": application.job.employment_type,
            "experience_required": application.job.experience_required,
            "required_skills": application.job.required_skills or [],
            "preferred_skills": application.job.preferred_skills or [],
            "description": application.job.description,
            "jd_analysis": application.job.jd_analysis,
        },
        candidate=candidate_service.to_out(db, candidate).model_dump(mode="json"),
        resume=resume_service.to_out(resume).model_dump(mode="json") if resume else None,
        screening=application_service.screening_out(screening) if screening else None,
        reviews=hitl_service.history(application),
    )


@router.post("/{application_id}/review", response_model=ReviewOut, status_code=201)
def submit_review(
    application_id: int,
    payload: ReviewRequest,
    recruiter: Recruiter = Depends(require_recruiter),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewOut:
    """The human decision. This is the only endpoint that sets a final status.

    The recruiter may agree with the AI or overrule it; either way the decision,
    the comment, the AI's recommendation and the timestamp are all stored.
    """
    application = application_service.get_for_recruiter(db, recruiter, application_id)
    review = hitl_service.submit_review(db, application, user, payload.decision, payload.comment)
    return application_service.review_out(review)


@router.get("/{application_id}/reviews", response_model=List[ReviewOut])
def review_history(
    application_id: int,
    recruiter: Recruiter = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> List[ReviewOut]:
    application = application_service.get_for_recruiter(db, recruiter, application_id)
    return hitl_service.history(application)
