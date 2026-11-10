from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import csv
import io
from fastapi import Query
from fastapi.responses import Response
from sqlalchemy import func
from app.auth import AccessIdentity
from app.dependencies import get_db, require_admin, require_operator
from app.models import Company, Conversation, Customer, Lead, Message, Opportunity, ProposalBrief
from app.schemas import (
    ActivityFeedResponse,
    ActivityItem,
    CompanyAgentConfig,
    CompanyCreate,
    EscalationAlert,
    EscalationResponse,
    EscalationRuleCreate,
    EscalationRuleResponse,
    FollowupConfigCreate,
    FollowupConfigResponse,
    GlobalSearchResponse,
    GlobalSearchResult,
    NotificationItem,
    NotificationResponse,
    ReplyTemplate,
    ReplyTemplateCreate,
)


# WP-204 — In-memory agent config store (no migration required)
# Keyed by company_id; values are dicts with system_prompt and/or temperature
_agent_config_store: dict[int, dict[str, object]] = {}

# WP-216 — In-memory agent usage tracking (no migration required)
# Keyed by company_id; values are dicts with total_calls, successful_calls, failed_calls
_agent_usage_store: dict[int, dict[str, int]] = {}

# WP-264 — In-memory reply templates store (no migration required)
# Keyed by company_id; values are lists of dicts with id, name, content
_reply_template_store: dict[int, list[dict[str, object]]] = {}
_reply_template_next_id: int = 1

# WP-521 — In-memory favorites store (no migration required)
# Keyed by (company_id, entity_type, entity_id); values are dicts with favorited_at
_favorites_store: dict[tuple[int, str, int], dict[str, object]] = {}


def _get_agent_usage(company_id: int) -> dict[str, int]:
    """Get agent usage stats for a company."""
    if company_id not in _agent_usage_store:
        _agent_usage_store[company_id] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
        }
    return _agent_usage_store[company_id]


def _record_agent_call(company_id: int, success: bool) -> None:
    """Record an agent call result."""
    usage = _get_agent_usage(company_id)
    usage["total_calls"] += 1
    if success:
        usage["successful_calls"] += 1
    else:
        usage["failed_calls"] += 1


router = APIRouter()


@router.post("/companies")
def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    _identity: AccessIdentity = Depends(require_admin),
):
    existing = db.scalar(
        select(Company).where(Company.slug == company.slug)
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Company slug already exists",
        )

    new_company = Company(
        name=company.name,
        slug=company.slug,
    )

    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    return new_company


@router.get("/companies")
def list_companies(
    db: Session = Depends(get_db),
    _identity: AccessIdentity = Depends(require_admin),
):
    return db.scalars(
        select(Company).order_by(Company.id)
    ).all()


@router.get("/companies/{company_id}/agent-config")
def get_agent_config(
    company_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Get the agent configuration for this company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    config = _agent_config_store.get(company_id, {})
    return CompanyAgentConfig(
        system_prompt=config.get("system_prompt"),
        temperature=config.get("temperature"),
        max_tokens=config.get("max_tokens"),
        model=config.get("model"),
    )


@router.put("/companies/{company_id}/agent-config")
def set_agent_config(
    company_id: int,
    data: CompanyAgentConfig,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Set the agent configuration for this company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    config: dict[str, object] = {}
    if data.system_prompt is not None:
        config["system_prompt"] = data.system_prompt
    if data.temperature is not None:
        config["temperature"] = data.temperature
    if data.max_tokens is not None:
        config["max_tokens"] = data.max_tokens
    if data.model is not None:
        config["model"] = data.model
    _agent_config_store[company_id] = config

    return CompanyAgentConfig(
        system_prompt=config.get("system_prompt"),
        temperature=config.get("temperature"),
        max_tokens=config.get("max_tokens"),
        model=config.get("model"),
    )


@router.get("/agent-models-available")
def get_agent_models_available():
    """WP-221 — List available Ollama models for configuration.

    Returns a static list of common Ollama models. This endpoint does not
    require authentication as it returns only public model metadata.
    """
    from app.database import settings

    # Build list of available models, always including the default
    models = [
        {"name": "qwen3:8b", "label": "Qwen3 8B (padrão)"},
        {"name": "qwen2.5:7b", "label": "Qwen2.5 7B"},
        {"name": "llama3.1:8b", "label": "Llama 3.1 8B"},
        {"name": "mistral:7b", "label": "Mistral 7B"},
        {"name": "gemma2:9b", "label": "Gemma2 9B"},
    ]

    # Mark the default model
    default_model = settings.ollama_model
    for m in models:
        m["is_default"] = m["name"] == default_model

    return {"models": models, "default": default_model}


@router.get("/companies/{company_id}/agent-usage")
def get_agent_usage(
    company_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Get agent usage statistics for this company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    usage = _get_agent_usage(company_id)
    return {
        "company_id": company_id,
        "total_calls": usage["total_calls"],
        "successful_calls": usage["successful_calls"],
        "failed_calls": usage["failed_calls"],
    }


# ---------------------------------------------------------------------------
# WP-264 — Reply templates
# ---------------------------------------------------------------------------


@router.get("/companies/{company_id}/reply-templates")
def list_reply_templates(
    company_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """List reply templates for this company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    templates = _reply_template_store.get(company_id, [])
    return [
        ReplyTemplate(id=t["id"], name=t["name"], content=t["content"])
        for t in templates
    ]


@router.post("/companies/{company_id}/reply-templates")
def create_reply_template(
    company_id: int,
    data: ReplyTemplateCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Create a new reply template for this company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    global _reply_template_next_id
    if company_id not in _reply_template_store:
        _reply_template_store[company_id] = []

    template = {
        "id": _reply_template_next_id,
        "name": data.name,
        "content": data.content,
    }
    _reply_template_next_id += 1
    _reply_template_store[company_id].append(template)

    return ReplyTemplate(id=template["id"], name=template["name"], content=template["content"])


@router.put("/companies/{company_id}/reply-templates/{template_id}")
def update_reply_template(
    company_id: int,
    template_id: int,
    data: ReplyTemplateCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Update a reply template belonging to this company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    for template in _reply_template_store.get(company_id, []):
        if template["id"] == template_id:
            template["name"] = data.name
            template["content"] = data.content
            return ReplyTemplate(id=template["id"], name=template["name"], content=template["content"])

    raise HTTPException(status_code=404, detail="Template not found")


@router.delete("/companies/{company_id}/reply-templates/{template_id}")
def delete_reply_template(
    company_id: int,
    template_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Delete a reply template."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    templates = _reply_template_store.get(company_id, [])
    for i, t in enumerate(templates):
        if t["id"] == template_id:
            templates.pop(i)
            return {"deleted": True}

    raise HTTPException(status_code=404, detail="Template not found")


@router.get("/companies/{company_id}/search")
def global_search(
    company_id: int,
    q: str = Query(min_length=1, max_length=200, description="Search query"),
    limit: int = Query(5, ge=1, le=20, description="Max results per entity type"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Search across all entity types for this company.

    Returns results grouped by entity type: opportunities, conversations,
    leads, and customers. Each result includes entity_type, entity_id,
    title, and an optional snippet.
    """
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    pattern = f"%{q}%"

    # Search opportunities
    opps = db.scalars(
        select(Opportunity)
        .where(Opportunity.company_id == company_id)
        .where(
            func.lower(Opportunity.title).like(func.lower(pattern)) |
            func.lower(Opportunity.description).like(func.lower(pattern))
        )
        .order_by(Opportunity.id)
        .limit(limit)
    ).all()
    opportunity_results = [
        GlobalSearchResult(
            entity_type="opportunity",
            entity_id=opp.id,
            title=opp.title or "",
            snippet=(opp.description or "")[:120],
        )
        for opp in opps
    ]

    # Search conversations
    convs = db.scalars(
        select(Conversation)
        .where(Conversation.company_id == company_id)
        .where(
            func.lower(Conversation.channel).like(func.lower(pattern))
        )
        .order_by(Conversation.id)
        .limit(limit)
    ).all()
    conversation_results = [
        GlobalSearchResult(
            entity_type="conversation",
            entity_id=conv.id,
            title=f"Conversa #{conv.id} · {conv.channel}",
            snippet=f"Status: {conv.status}",
        )
        for conv in convs
    ]

    # Search leads
    leads = db.scalars(
        select(Lead)
        .where(Lead.company_id == company_id)
        .where(
            func.lower(Lead.name).like(func.lower(pattern)) |
            func.lower(Lead.phone).like(func.lower(pattern))
        )
        .order_by(Lead.id)
        .limit(limit)
    ).all()
    lead_results = [
        GlobalSearchResult(
            entity_type="lead",
            entity_id=lead.id,
            title=lead.name or "Sem nome",
            snippet=lead.phone or "",
        )
        for lead in leads
    ]

    # Search customers
    custs = db.scalars(
        select(Customer)
        .where(Customer.company_id == company_id)
        .where(
            func.lower(Customer.name).like(func.lower(pattern)) |
            func.lower(Customer.phone).like(func.lower(pattern))
        )
        .order_by(Customer.id)
        .limit(limit)
    ).all()
    customer_results = [
        GlobalSearchResult(
            entity_type="customer",
            entity_id=cust.id,
            title=cust.name or "Sem nome",
            snippet=cust.phone or "",
        )
        for cust in custs
    ]

    return GlobalSearchResponse(
        opportunities=opportunity_results,
        conversations=conversation_results,
        leads=lead_results,
        customers=customer_results,
    )


@router.get("/companies/{company_id}/activity")
def get_activity_feed(
    company_id: int,
    limit: int = Query(20, ge=1, le=100, description="Max activity items"),
    period: str = Query("7d", pattern=r"^(7d|30d|90d)$", description="Time period: 7d, 30d, or 90d"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Get recent activity feed for this company.

    Aggregates activities from opportunities, briefs, conversations,
    and leads within the specified time period.
    """
    from datetime import timedelta

    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Calculate cutoff date
    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    from datetime import datetime, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    items: list[ActivityItem] = []

    # Opportunity created
    opps = db.scalars(
        select(Opportunity)
        .where(Opportunity.company_id == company_id)
        .where(Opportunity.created_at >= cutoff)
        .order_by(Opportunity.created_at.desc())
    ).all()
    for opp in opps:
        items.append(ActivityItem(
            activity_type="opportunity_created",
            entity_id=opp.id,
            title=f"Oportunidade criada: {opp.title}",
            timestamp=opp.created_at,
        ))

    # Opportunity closed
    for opp in opps:
        if opp.closed_at and opp.closed_at >= cutoff:
            outcome_label = "ganha" if opp.outcome == "won" else "perdida"
            items.append(ActivityItem(
                activity_type="opportunity_closed",
                entity_id=opp.id,
                title=f"Oportunidade {outcome_label}: {opp.title}",
                timestamp=opp.closed_at,
            ))

    # Brief approved/rejected
    briefs = db.scalars(
        select(ProposalBrief)
        .join(Opportunity)
        .where(Opportunity.company_id == company_id)
        .where(ProposalBrief.decided_at.isnot(None))
        .where(ProposalBrief.decided_at >= cutoff)
        .order_by(ProposalBrief.decided_at.desc())
    ).all()
    for brief in briefs:
        opp = db.scalar(select(Opportunity).where(Opportunity.id == brief.opportunity_id))
        status_label = "aprovado" if brief.status == "approved" else "rejeitado"
        items.append(ActivityItem(
            activity_type="brief_approved" if brief.status == "approved" else "brief_rejected",
            entity_id=brief.id,
            title=f"Brief {status_label}: {opp.title if opp else 'N/A'}",
            timestamp=brief.decided_at,
        ))

    # Conversation replied (agent messages)
    convs = db.scalars(
        select(Conversation)
        .where(Conversation.company_id == company_id)
        .where(Conversation.updated_at >= cutoff)
        .order_by(Conversation.updated_at.desc())
    ).all()
    for conv in convs:
        # Check if there are agent messages in this conversation
        has_reply = db.scalar(
            select(Message.id)
            .where(Message.conversation_id == conv.id)
            .where(Message.sender_type == "agent")
        ) is not None
        if has_reply:
            items.append(ActivityItem(
                activity_type="conversation_replied",
                entity_id=conv.id,
                title=f"Resposta enviada: conversa #{conv.id} ({conv.channel})",
                timestamp=conv.updated_at,
            ))

    # Lead converted
    leads = db.scalars(
        select(Lead)
        .where(Lead.company_id == company_id)
        .where(Lead.status == "converted")
        .where(Lead.updated_at >= cutoff)
        .order_by(Lead.updated_at.desc())
    ).all()
    for lead in leads:
        items.append(ActivityItem(
            activity_type="lead_converted",
            entity_id=lead.id,
            title=f"Lead convertido: {lead.name}",
            timestamp=lead.updated_at,
        ))

    # Sort by timestamp descending and limit
    items.sort(key=lambda x: x.timestamp, reverse=True)
    items = items[:limit]

    return ActivityFeedResponse(items=items)


@router.get("/companies/{company_id}/report")
def export_dashboard_report(
    company_id: int,
    period: str = Query("7d", pattern=r"^(7d|30d|90d)$", description="Time period: 7d, 30d, or 90d"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Export dashboard metrics as CSV.

    Returns a CSV with consolidated metrics: opportunities, conversations,
    leads, customers, and briefs counts for the specified period.
    """
    from datetime import datetime, timedelta, timezone

    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Count opportunities
    total_opps = db.scalar(
        select(func.count(Opportunity.id))
        .where(Opportunity.company_id == company_id)
    ) or 0
    recent_opps = db.scalar(
        select(func.count(Opportunity.id))
        .where(Opportunity.company_id == company_id)
        .where(Opportunity.created_at >= cutoff)
    ) or 0
    closed_opps = db.scalar(
        select(func.count(Opportunity.id))
        .where(Opportunity.company_id == company_id)
        .where(Opportunity.closed_at.isnot(None))
    ) or 0
    won_opps = db.scalar(
        select(func.count(Opportunity.id))
        .where(Opportunity.company_id == company_id)
        .where(Opportunity.outcome == "won")
    ) or 0

    # Count conversations
    total_convs = db.scalar(
        select(func.count(Conversation.id))
        .where(Conversation.company_id == company_id)
    ) or 0
    open_convs = db.scalar(
        select(func.count(Conversation.id))
        .where(Conversation.company_id == company_id)
        .where(Conversation.status == "open")
    ) or 0

    # Count leads
    total_leads = db.scalar(
        select(func.count(Lead.id))
        .where(Lead.company_id == company_id)
    ) or 0
    converted_leads = db.scalar(
        select(func.count(Lead.id))
        .where(Lead.company_id == company_id)
        .where(Lead.status == "converted")
    ) or 0

    # Count customers
    total_customers = db.scalar(
        select(func.count(Customer.id))
        .where(Customer.company_id == company_id)
    ) or 0

    # Count briefs
    total_briefs = db.scalar(
        select(func.count(ProposalBrief.id))
        .join(Opportunity)
        .where(Opportunity.company_id == company_id)
    ) or 0
    approved_briefs = db.scalar(
        select(func.count(ProposalBrief.id))
        .join(Opportunity)
        .where(Opportunity.company_id == company_id)
        .where(ProposalBrief.status == "approved")
    ) or 0

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    writer.writerow(["period", period])
    writer.writerow(["total_opportunities", total_opps])
    writer.writerow(["recent_opportunities", recent_opps])
    writer.writerow(["closed_opportunities", closed_opps])
    writer.writerow(["won_opportunities", won_opps])
    writer.writerow(["total_conversations", total_convs])
    writer.writerow(["open_conversations", open_convs])
    writer.writerow(["total_leads", total_leads])
    writer.writerow(["converted_leads", converted_leads])
    writer.writerow(["total_customers", total_customers])
    writer.writerow(["total_briefs", total_briefs])
    writer.writerow(["approved_briefs", approved_briefs])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=dashboard_report_{period}.csv",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get("/companies/{company_id}/notifications")
def get_notifications(
    company_id: int,
    since: str | None = Query(None, description="Only notifications after this ISO timestamp"),
    limit: int = Query(20, ge=1, le=100, description="Max notifications"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Get notifications for this company.

    Returns notifications based on recent activity: new opportunities,
    briefs pending review, briefs approved/rejected.
    """
    from datetime import datetime, timezone

    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

    notifications: list[NotificationItem] = []

    # Briefs pending review
    pending_briefs = db.scalars(
        select(ProposalBrief)
        .join(Opportunity)
        .where(Opportunity.company_id == company_id)
        .where(ProposalBrief.status == "draft")
        .where(ProposalBrief.created_at >= since_dt if since_dt else True)
        .order_by(ProposalBrief.created_at.desc())
    ).all()
    for brief in pending_briefs:
        opp = db.scalar(select(Opportunity).where(Opportunity.id == brief.opportunity_id))
        notifications.append(NotificationItem(
            notification_type="brief_pending",
            entity_id=brief.id,
            title=f"Brief pendente: {opp.title if opp else 'N/A'}",
            timestamp=brief.created_at,
        ))

    # Briefs approved/rejected
    decided_briefs = db.scalars(
        select(ProposalBrief)
        .join(Opportunity)
        .where(Opportunity.company_id == company_id)
        .where(ProposalBrief.decided_at.isnot(None))
        .where(ProposalBrief.decided_at >= since_dt if since_dt else True)
        .order_by(ProposalBrief.decided_at.desc())
    ).all()
    for brief in decided_briefs:
        opp = db.scalar(select(Opportunity).where(Opportunity.id == brief.opportunity_id))
        status_label = "aprovado" if brief.status == "approved" else "rejeitado"
        notifications.append(NotificationItem(
            notification_type="brief_approved" if brief.status == "approved" else "brief_rejected",
            entity_id=brief.id,
            title=f"Brief {status_label}: {opp.title if opp else 'N/A'}",
            timestamp=brief.decided_at,
        ))

    # New opportunities (last 24h)
    from datetime import timedelta
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    if since_dt:
        recent_cutoff = max(recent_cutoff, since_dt)
    new_opps = db.scalars(
        select(Opportunity)
        .where(Opportunity.company_id == company_id)
        .where(Opportunity.created_at >= recent_cutoff)
        .order_by(Opportunity.created_at.desc())
    ).all()
    for opp in new_opps:
        notifications.append(NotificationItem(
            notification_type="new_opportunity",
            entity_id=opp.id,
            title=f"Nova oportunidade: {opp.title}",
            timestamp=opp.created_at,
        ))

    # Sort by timestamp descending and limit
    notifications.sort(key=lambda x: x.timestamp, reverse=True)
    notifications = notifications[:limit]

    unread = [n for n in notifications if n.read is False]

    return NotificationResponse(
        notifications=notifications,
        unread_count=len(unread),
    )


# ---------------------------------------------------------------------------
# WP-534 — Rate limit status endpoint
# ---------------------------------------------------------------------------


@router.get("/companies/{company_id}/rate-limit-status")
def get_rate_limit_status(
    company_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Get the AI rate limit status for this company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if identity.company_id and identity.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from app.services.rate_limiter import rate_limiter

    return rate_limiter.status(company_id)


# ---------------------------------------------------------------------------
# WP-535 — Agent health check endpoint
# ---------------------------------------------------------------------------


@router.get("/companies/{company_id}/agent-health")
def agent_health(
    company_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Check if the AI agent provider is available."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if identity.company_id and identity.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from app.services.agent import get_provider

    provider = get_provider()
    return provider.health_check()


# ---------------------------------------------------------------------------
# WP-544 — Escalation endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/companies/{company_id}/escalation-rules",
    response_model=EscalationRuleResponse,
)
def create_escalation_rule(
    company_id: int,
    data: EscalationRuleCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Create an escalation rule for a company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if identity.company_id and identity.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from app.services.escalation import EscalationRule, add_escalation_rule

    rule = EscalationRule(
        name=data.name,
        company_id=company_id,
        max_response_minutes=data.max_response_minutes,
        enabled=data.enabled,
    )
    add_escalation_rule(rule)
    return EscalationRuleResponse(
        name=rule.name,
        max_response_minutes=rule.max_response_minutes,
        enabled=rule.enabled,
    )


@router.get(
    "/companies/{company_id}/escalations",
    response_model=EscalationResponse,
)
def get_escalations(
    company_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Check for conversations that need escalation."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if identity.company_id and identity.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from app.services.escalation import check_escalations, get_escalation_rules

    alerts = check_escalations(db, company_id)
    rules = get_escalation_rules(company_id)

    return EscalationResponse(
        alerts=[
            EscalationAlert(
                conversation_id=a.conversation_id,
                conversation_title=a.conversation_title,
                last_customer_message_at=a.last_customer_message_at.isoformat(),
                minutes_since_response=a.minutes_since_response,
                rule_name=a.rule_name,
            )
            for a in alerts
        ],
        rules=[
            EscalationRuleResponse(
                name=r.name,
                max_response_minutes=r.max_response_minutes,
                enabled=r.enabled,
            )
            for r in rules
        ],
    )


@router.get(
    "/companies/{company_id}/escalation-rules",
    response_model=list[EscalationRuleResponse],
)
def list_escalation_rules(
    company_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """List all escalation rules for a company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if identity.company_id and identity.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from app.services.escalation import get_escalation_rules

    rules = get_escalation_rules(company_id)
    return [
        EscalationRuleResponse(
            name=r.name,
            max_response_minutes=r.max_response_minutes,
            enabled=r.enabled,
        )
        for r in rules
    ]


@router.delete(
    "/companies/{company_id}/escalation-rules/{rule_name}",
    response_model=bool,
)
def delete_escalation_rule(
    company_id: int,
    rule_name: str,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Delete an escalation rule."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if identity.company_id and identity.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from app.services.escalation import remove_escalation_rule

    removed = remove_escalation_rule(company_id, rule_name)
    if not removed:
        raise HTTPException(status_code=404, detail="Rule not found")
    return True


# ---------------------------------------------------------------------------
# WP-545 — Follow-up config endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/companies/{company_id}/followup-config",
    response_model=FollowupConfigResponse,
)
def set_followup_config(
    company_id: int,
    data: FollowupConfigCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Set follow-up config for a company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if identity.company_id and identity.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from app.services.followup import FollowupConfig, set_followup_config as _set

    config = FollowupConfig(
        company_id=company_id,
        stale_days=data.stale_days,
        enabled=data.enabled,
    )
    _set(config)
    return FollowupConfigResponse(
        stale_days=config.stale_days,
        enabled=config.enabled,
    )


@router.get(
    "/companies/{company_id}/followup-config",
    response_model=FollowupConfigResponse | None,
)
def get_company_followup_config(
    company_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Get follow-up config for a company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if identity.company_id and identity.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from app.services.followup import get_followup_config as _get

    config = _get(company_id)
    if config is None:
        return None
    return FollowupConfigResponse(
        stale_days=config.stale_days,
        enabled=config.enabled,
    )
