"""Private commercial intake evaluate endpoint.

This router exposes the WP-035 + WP-036 intake engine as an authenticated,
internal-only endpoint.  It does NOT persist data, send messages, call n8n,
or publish any webhook.
"""

from fastapi import APIRouter, Depends, status

from app.dependencies import get_intake_generator, require_operator
from app.database import settings
from app.schemas import CommercialIntakeEvaluateRequest
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
