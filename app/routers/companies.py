from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import Query
from sqlalchemy import func
from app.auth import AccessIdentity
from app.dependencies import get_db, require_admin, require_operator
from app.models import Company, Conversation, Customer, Lead, Opportunity
from app.schemas import (
    CompanyAgentConfig,
    CompanyCreate,
    GlobalSearchResponse,
    GlobalSearchResult,
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
