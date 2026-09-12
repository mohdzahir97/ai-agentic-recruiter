"""Human-in-the-loop review — the only path to a final decision.

Nothing in the AI layer writes SHORTLISTED, ON_HOLD or REJECTED. Only
`submit_review()` does, and it always records who decided, what the AI had
recommended at that moment, and whether the human disagreed.

`overrode_ai` is the number worth watching: it is how you find out whether the
model is actually being trusted, or quietly ignored.
"""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models import (
    AIScreening,
    Application,
    DECISION_TO_STATUS,
    HitlDecision,
    HitlReview,
    Recommendation,
    User,
)
from app.schemas.application import ReviewOut

logger = logging.getLogger(__name__)

# What the AI's label implies, if a human simply agreed with it. Used only to
# work out whether a decision was an override — never to decide anything.
_IMPLIED_DECISION = {
    Recommendation.STRONG_MATCH: HitlDecision.SHORTLIST,
    Recommendation.GOOD_MATCH: HitlDecision.SHORTLIST,
    Recommendation.PARTIAL_MATCH: HitlDecision.HOLD,
    Recommendation.WEAK_MATCH: HitlDecision.REJECT,
}


def submit_review(
    db: Session,
    application: Application,
    reviewer: User,
    decision: HitlDecision,
    comment: Optional[str],
) -> HitlReview:
    screening: Optional[AIScreening] = application.latest_screening

    # A REJECT that goes against the AI is exactly the case where the reason
    # matters most, so it is the one case a comment is required.
    if decision is HitlDecision.REJECT and not (comment or "").strip():
        raise ValidationError("Please give a reason when rejecting a candidate")

    overrode = _is_override(screening, decision)

    review = HitlReview(
        application_id=application.id,
        screening_id=screening.id if screening else None,
        reviewer_user_id=reviewer.id,
        ai_recommendation=screening.recommendation if screening else None,
        ai_score=screening.overall_match if screening else None,
        ai_confidence=screening.confidence if screening else None,
        decision=decision.value,
        comment=(comment or "").strip() or None,
        overrode_ai=overrode,
    )
    db.add(review)

    application.status = DECISION_TO_STATUS[decision].value

    db.commit()
    db.refresh(review)
    logger.info(
        "Application %s decided %s by user %s (AI said %s; override=%s)",
        application.id,
        decision.value,
        reviewer.id,
        review.ai_recommendation,
        overrode,
    )
    return review


def _is_override(screening: Optional[AIScreening], decision: HitlDecision) -> bool:
    if not screening:
        return False  # no AI opinion to override
    try:
        implied = _IMPLIED_DECISION[Recommendation(screening.recommendation)]
    except ValueError:
        return False
    return implied is not decision


def history(application: Application) -> List[ReviewOut]:
    from app.services.application_service import review_out

    return [review_out(review) for review in application.reviews]
