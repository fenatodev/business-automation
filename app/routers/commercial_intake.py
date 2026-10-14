"""Private commercial intake evaluate endpoint.

This router exposes the WP-035 + WP-036 intake engine as an authenticated,
internal-only endpoint.  It does NOT persist data, send messages, call n8n,
or publish any webhook.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_intake_generator, require_operator
from app.database import settings
from app.schemas import CommercialIntakeEvaluateRequest
from app.services.commercial_intake import (
    CandidateReply,
    CommercialIntakeEvent,
    IntakeDecision,
)
from app.services.intake_candidate_generator import (
    CandidateGenerator,
    CandidateGenerationError,
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

    try:
        decision = evaluate_intake(event, generator)
    except CandidateGenerationError:
        # evaluate_intake already handles this, but guard against any leak
        decision = IntakeDecision(
            event_id=request.event_id,
            intent="unknown",
            next_step="ask_clarification",
            draft_reply=(
                "No momento não conseguimos processar sua mensagem "
                "automaticamente. Um especialista irá analisar e retornar "
                "em breve."
            ),
            needs_human_review=True,
            can_send=False,
            flags=["provider_unavailable"],
            simulation_only=True,
        )
    except Exception:
        # Catch-all for unexpected errors — never leak internals
        decision = IntakeDecision(
            event_id=request.event_id,
            intent="unknown",
            next_step="ask_clarification",
            draft_reply=(
                "No momento não conseguimos processar sua mensagem "
                "automaticamente. Um especialista irá analisar e retornar "
                "em breve."
            ),
            needs_human_review=True,
            can_send=False,
            flags=["internal_error"],
            simulation_only=True,
        )

    return decision
