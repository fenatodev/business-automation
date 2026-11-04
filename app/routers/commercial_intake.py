"""Private commercial intake endpoints.

This router exposes the WP-035 + WP-036 intake engine as an authenticated,
internal-only endpoint.  The evaluate endpoint is simulation-only.
The create endpoint evaluates and persists as an Opportunity.
The suggest endpoint uses AI to pre-predict intent before submission.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, get_intake_generator, require_operator
from app.database import settings
from app.models import Company, Opportunity
from app.schemas import (
    CommercialIntakeEvaluateRequest,
    IntakeCreate,
    IntakeCreateResponse,
    IntakeSuggestion,
)
from app.services.agent import AgentServiceError, generate_agent_reply
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


# ---------------------------------------------------------------------------
# WP-258 — AI-assisted intake suggestion
# ---------------------------------------------------------------------------

_INTAKE_SUGGEST_SYSTEM_PROMPT = """Você é um assistente de classificação de intake comercial.
Analise a mensagem e retorne APENAS um JSON com:
{
  "suggested_intent": "a intenção principal (ex: orçamento, informação, suporte, parceria)",
  "suggested_category": "categoria (ex: produto, serviço, projeto)",
  "reasoning": "explicação breve da classificação",
  "confidence": 0.9
}
Não inclua nada além do JSON."""


@router.post(
    "/internal/commercial-intake/suggest",
    response_model=IntakeSuggestion,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def suggest_intake(
    request: IntakeCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
) -> IntakeSuggestion:
    """Use AI to suggest intent and category before creating the intake.

    This endpoint analyzes the message and returns a suggestion for
    pre-validation. The operator can accept or correct before submission.
    Returns 503 if the AI service is unavailable.
    """
    # Get company agent config for customization
    company = db.scalar(
        select(Company).where(Company.id == identity.company_id)
    )
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    # Load company agent config (in-memory store)
    agent_config = _get_agent_config_store().get(identity.company_id)

    system_prompt = (agent_config.get("system_prompt") if agent_config else None) or _INTAKE_SUGGEST_SYSTEM_PROMPT
    temperature = agent_config.get("temperature") if agent_config else None
    max_tokens = agent_config.get("max_tokens") if agent_config else None
    model = agent_config.get("model") if agent_config else None

    try:
        reply = generate_agent_reply(
            message=request.message,
            history=[],
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
    except AgentServiceError:
        raise HTTPException(
            status_code=503,
            detail="Serviço de agente indisponível. Tente novamente mais tarde.",
        )

    # Parse JSON response with fallback
    try:
        data = json.loads(reply)
        return IntakeSuggestion(
            suggested_intent=data.get("suggested_intent", "unknown"),
            suggested_category=data.get("suggested_category"),
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence"),
        )
    except (json.JSONDecodeError, AttributeError):
        # Fallback: return raw reply as reasoning
        return IntakeSuggestion(
            suggested_intent="unknown",
            reasoning=str(reply)[:500],
        )


# In-memory store for agent configs (shared with conversations router)
_agent_config_store: dict[int, dict] = {}


def _get_agent_config_store() -> dict[int, dict]:
    """Return the shared in-memory agent config store."""
    return _agent_config_store
