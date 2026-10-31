"""Private commercial intake endpoints.

This router exposes the WP-035 + WP-036 intake engine as an authenticated,
internal-only endpoint.  The evaluate endpoint is simulation-only.
The create endpoint evaluates and persists as an Opportunity.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_intake_generator, require_operator
from app.database import settings
from app.models import Opportunity
from app.schemas import (
    CommercialIntakeEvaluateRequest,
    IntakeCreate,
    IntakeCreateResponse,
)
from app.services.commercial_intake import (
    CommercialIntakeEvent,
    IntakeDecision,
)
from app.services.intake_candidate_generator import (
    CandidateGenerator,
    evaluate_intake,
)

router = APIRouter()


@router.post(
    "/internal/commercial-intake/evaluate",
    response_model=IntakeDecision,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def evaluate_commercial_intake(
    request: CommercialIntakeEvaluateRequest,
    _identity: dict = Depends(require_operator),
    generator: CandidateGenerator = Depends(get_intake_generator),
) -> IntakeDecision:
    """Evaluate a commercial intake event and return a structured decision.

    This endpoint is private, authenticated, and simulation-only.
    It never writes to the database, sends messages, or calls external services
    beyond the configured local candidate generator.
    """
    event = CommercialIntakeEvent(
        channel=request.channel,
        message=request.message,
        service_context=settings.intake_service_context,
        event_id=request.event_id,
    )

    return evaluate_intake(event, generator)


@router.post(
    "/internal/commercial-intake/create",
    response_model=IntakeCreateResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def create_commercial_intake(
    request: IntakeCreate,
    db: Session = Depends(get_db),
    identity: dict = Depends(require_operator),
    generator: CandidateGenerator = Depends(get_intake_generator),
) -> IntakeCreateResponse:
    """Evaluate a commercial intake event and persist it as an Opportunity.

    This endpoint evaluates the intake, creates an Opportunity record,
    and returns the decision along with the opportunity ID.
    Deduplication is handled by event_id within the tenant.
    """
    event = CommercialIntakeEvent(
        channel=request.channel,
        message=request.message,
        service_context=settings.intake_service_context,
        event_id=request.event_id,
    )

    decision = evaluate_intake(event, generator)

    # Access company_id from AccessIdentity object
    company_id = identity.company_id if hasattr(identity, "company_id") else identity["company_id"]

    # Deduplication: check if event_id already exists for this tenant
    existing = (
        db.query(Opportunity)
        .filter(
            Opportunity.company_id == company_id,
            Opportunity.source == "intake",
            Opportunity.external_url == f"intake://{request.event_id}",
        )
        .first()
    )
    if existing is not None:
        return IntakeCreateResponse(
            opportunity_id=existing.id,
            event_id=decision.event_id,
            intent=decision.intent,
            needs_human_review=decision.needs_human_review,
            flags=decision.flags,
        )

    # Build opportunity title from intent and message
    title = f"Intake: {decision.intent}" if decision.intent != "unknown" else "Intake comercial"
    # Truncate message for description, add triage note
    description = (
        request.message[:1000]
        + f"\n\n[Triage: intenção={decision.intent}, revisão={decision.needs_human_review}]"
    )

    opp = Opportunity(
        company_id=company_id,
        source="intake",
        external_url=f"intake://{request.event_id}",
        title=title,
        description=description,
        captured_at=datetime.now(timezone.utc),
    )
    db.add(opp)
    try:
        db.commit()
        db.refresh(opp)
    except IntegrityError:
        db.rollback()
        # Race condition: another request created the same event_id
        existing = (
            db.query(Opportunity)
            .filter(
                Opportunity.company_id == company_id,
                Opportunity.source == "intake",
                Opportunity.external_url == f"intake://{request.event_id}",
            )
            .first()
        )
        if existing is not None:
            return IntakeCreateResponse(
                opportunity_id=existing.id,
                event_id=decision.event_id,
                intent=decision.intent,
                needs_human_review=decision.needs_human_review,
                flags=decision.flags,
            )
        raise HTTPException(status_code=500, detail="Falha ao criar oportunidade.")

    return IntakeCreateResponse(
        opportunity_id=opp.id,
        event_id=decision.event_id,
        intent=decision.intent,
        needs_human_review=decision.needs_human_review,
        flags=decision.flags,
    )
