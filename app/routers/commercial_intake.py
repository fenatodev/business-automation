"""Private commercial intake evaluate endpoint.

This router exposes the WP-035 + WP-036 intake engine as an authenticated,
internal-only endpoint.  It does NOT persist data, send messages, call n8n,
or publish any webhook.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, get_intake_generator, require_operator
from app.database import settings
from app.models import Company, Opportunity
from app.schemas import (
    CommercialIntakeEvaluateRequest,
    IntakeCreate,
    IntakeCreateResponse,
)
from app.services.commercial_intake import (
    CandidateReply,
    CommercialIntakeEvent,
    IntakeDecision,
    process_commercial_intake,
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
def create_intake_opportunity(
    request: IntakeCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
    generator: CandidateGenerator = Depends(get_intake_generator),
) -> IntakeCreateResponse:
    """Evaluate a commercial intake and persist it as an opportunity.

    This endpoint is private, authenticated, and tenant-isolated.
    It creates an Opportunity from the intake event after evaluation.
    No external messages are sent.
    """
    company = db.scalar(select(Company).where(Company.id == identity.company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    # Check for duplicate by event_id
    existing = db.scalar(
        select(Opportunity).where(
            Opportunity.company_id == identity.company_id,
            Opportunity.external_url == f"intake:{request.event_id}",
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Intake already captured",
        )

    # Evaluate the intake
    event = CommercialIntakeEvent(
        channel=request.channel,
        message=request.message,
        service_context=settings.intake_service_context,
        event_id=request.event_id,
    )

    # Get candidate reply from generator
    candidate = generator.generate(event)
    decision = process_commercial_intake(event, candidate)

    # Create opportunity from intake
    now = datetime.now(timezone.utc)
    title = f"Intake: {request.message[:150]}"
    if len(request.message) > 150:
        title = f"Intake: {request.message[:147]}..."

    triage_note = None
    if decision.needs_human_review:
        triage_note = f"Flags: {', '.join(decision.flags)}"

    opportunity = Opportunity(
        company_id=identity.company_id,
        source="intake",
        external_url=f"intake:{request.event_id}",
        title=title,
        description=request.message,
        budget=None,
        deadline=None,
        requirements=None,
        captured_at=now,
        next_action="pending",
        triage_note=triage_note,
    )

    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)

    return IntakeCreateResponse(
        decision=decision.model_dump(),
        opportunity_id=opportunity.id,
    )
