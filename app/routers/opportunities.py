import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import desc, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, require_operator
from app.models import Company, Conversation, Customer, Lead, Opportunity, ProposalBrief
from app.schemas import (
    FavoriteResponse,
    FavoriteToggle,
    OpportunityBulkDelete,
    OpportunityBulkTriage,
    OpportunityBulkTriageSuggestion,
    OpportunityBulkTriageSuggestionResponse,
    OpportunityClose,
    OpportunityCreate,
    OpportunityTriageSuggestion,
    OpportunityTriageUpdate,
    OpportunityUpdate,
    ProposalBriefBulkDelete,
    ProposalBriefBulkStatus,
    ProposalBriefCreate,
    ProposalBriefDecision,
    ProposalBriefSuggestion,
    ProposalBriefUpdate,
    StaleOpportunityResponse,
    StaleOpportunitiesResponse,
)
from app.routers.companies import _favorites_store


router = APIRouter()


def _get_tenant_opportunity(
    db: Session,
    opportunity_id: int,
    company_id: int,
) -> Opportunity:
    opportunity = db.scalar(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.company_id == company_id,
        )
    )

    if opportunity is None:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found",
        )

    return opportunity


def _duplicate_exists(
    db: Session,
    company_id: int,
    external_url: str,
) -> bool:
    return (
        db.scalar(
            select(Opportunity.id).where(
                Opportunity.company_id == company_id,
                Opportunity.external_url == external_url,
            )
        )
        is not None
    )


@router.post("/opportunities")
def create_opportunity(
    data: OpportunityCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    company = db.scalar(
        select(Company).where(Company.id == identity.company_id)
    )
    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    if _duplicate_exists(
        db,
        identity.company_id,
        data.external_url,
    ):
        raise HTTPException(
            status_code=409,
            detail="Opportunity already captured",
        )

    opportunity = Opportunity(
        company_id=identity.company_id,
        source=data.source,
        external_url=data.external_url,
        title=data.title,
        description=data.description,
        budget=data.budget,
        deadline=data.deadline,
        requirements=data.requirements,
        captured_at=data.captured_at,
        lead_id=data.lead_id,
        customer_id=data.customer_id,
        next_action="pending",
    )

    if data.lead_id is not None and db.scalar(select(Lead.id).where(
        Lead.id == data.lead_id, Lead.company_id == identity.company_id,
    )) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    if data.customer_id is not None and db.scalar(select(Customer.id).where(
        Customer.id == data.customer_id, Customer.company_id == identity.company_id,
    )) is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    db.add(opportunity)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        if _duplicate_exists(
            db,
            identity.company_id,
            data.external_url,
        ):
            raise HTTPException(
                status_code=409,
                detail="Opportunity already captured",
            )

        raise

    db.refresh(opportunity)
    return opportunity


@router.post("/opportunities/import.csv")
def import_opportunities_csv(
    file: UploadFile,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Import opportunities from a CSV file.

    Expected columns: Título, Descrição, URL (optional), Orçamento (optional),
    Prazo (optional), Requisitos (optional).
    Duplicate external_url values are skipped. Max 500 rows per import.
    Returns: {imported, skipped, errors}
    """
    if file.content_type not in ("text/csv", "application/csv", None):
        raise HTTPException(
            status_code=400,
            detail="Apenas arquivos CSV são aceitos",
        )

    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    # Validate header
    if reader.fieldnames is None:
        raise HTTPException(
            status_code=400,
            detail="Arquivo CSV vazio ou inválido",
        )

    required_columns = {"Título", "Descrição"}
    available = set(reader.fieldnames or [])
    if not required_columns.issubset(available):
        raise HTTPException(
            status_code=400,
            detail=f"Colunas obrigatórias ausentes: {required_columns - available}",
        )

    # Load existing external URLs for deduplication
    existing_urls = {
        row[0]
        for row in db.execute(
            select(Opportunity.external_url).where(
                Opportunity.company_id == identity.company_id
            )
        ).fetchall()
    }

    imported = 0
    skipped = 0
    errors = 0
    max_rows = 500
    row_count = 0
    now = datetime.now()

    for row in reader:
        if row_count >= max_rows:
            break
        row_count += 1

        title = (row.get("Título") or "").strip()
        description = (row.get("Descrição") or "").strip()
        external_url = (row.get("URL") or "").strip()
        budget = (row.get("Orçamento") or "").strip() or None
        deadline = (row.get("Prazo") or "").strip() or None
        requirements = (row.get("Requisitos") or "").strip() or None

        if not title or not description:
            errors += 1
            continue

        # Generate a unique external_url if not provided
        if not external_url:
            external_url = f"import-{row_count}-{imported}"

        if external_url in existing_urls:
            skipped += 1
            continue

        opportunity = Opportunity(
            company_id=identity.company_id,
            source="import",
            external_url=external_url,
            title=title,
            description=description,
            budget=budget,
            deadline=deadline,
            requirements=requirements,
            captured_at=now,
            next_action="pending",
        )
        db.add(opportunity)
        existing_urls.add(external_url)
        imported += 1

    db.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "total_processed": row_count,
    }


@router.get("/opportunities")
def list_opportunities(
    exclude_archived: bool = False,
    next_action: str | None = Query(None, description="Filter by next_action status"),
    source: str | None = Query(None, description="Filter by source"),
    q: str | None = Query(None, description="Search keywords in title and description"),
    from_date: str | None = Query(None, description="Filter captured_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter captured_at <= date (YYYY-MM-DD)"),
    lead_id: int | None = Query(None, description="Filter opportunities with conversations linked to this lead"),
    customer_id: int | None = Query(None, description="Filter opportunities with conversations linked to this customer"),
    priority_level: str | None = Query(None, description="Filter by priority level: high, medium, low"),
    sort: str = Query(default="id", description="Sort by: id, created_at, next_action"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """List opportunities with optional filters, search, sort, and pagination."""
    stmt = (
        select(Opportunity)
        .where(Opportunity.company_id == identity.company_id)
    )

    if exclude_archived:
        stmt = stmt.where(Opportunity.next_action.notin_(["done", "lost"]))

    if next_action is not None:
        stmt = stmt.where(Opportunity.next_action == next_action)

    if source is not None:
        stmt = stmt.where(Opportunity.source == source)

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            func.lower(Opportunity.title).like(func.lower(pattern)) |
            func.lower(Opportunity.description).like(func.lower(pattern))
        )

    # WP-149 — date range filter on captured_at (ISO 8601 string comparison)
    if from_date:
        stmt = stmt.where(Opportunity.captured_at >= from_date)
    if to_date:
        stmt = stmt.where(Opportunity.captured_at <= to_date + "T23:59:59")

    # WP-263 — filter by lead_id or customer_id via conversations
    if lead_id is not None:
        stmt = stmt.where(
            exists().where(
                (Conversation.company_id == identity.company_id)
                & (Conversation.lead_id == lead_id)
            )
        )
    if customer_id is not None:
        stmt = stmt.where(
            exists().where(
                (Conversation.company_id == identity.company_id)
                & (Conversation.customer_id == customer_id)
            )
        )

    if sort == "created_at":
        stmt = stmt.order_by(desc(Opportunity.created_at), desc(Opportunity.id))
    elif sort == "next_action":
        stmt = stmt.order_by(Opportunity.next_action, Opportunity.id)
    else:
        stmt = stmt.order_by(Opportunity.id)

    opportunities = db.scalars(stmt).all()

    # WP-266 — filter by priority level (computed in-memory)
    if priority_level is not None:
        opportunities = [
            opp for opp in opportunities
            if _calculate_priority_score(opp)["level"] == priority_level
        ]

    # Apply pagination after priority filter
    return opportunities[offset:offset + limit]


@router.get("/opportunities/export")
def export_opportunities_csv(
    next_action: str | None = Query(None, description="Filter by next_action status"),
    source: str | None = Query(None, description="Filter by source"),
    q: str | None = Query(None, description="Search keywords in title and description"),
    from_date: str | None = Query(None, description="Filter captured_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter captured_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Export opportunities to CSV with optional filters.

    Returns a CSV file with columns: id, source, title, description, budget,
    deadline, next_action, outcome, final_value, captured_at, created_at.
    """
    stmt = (
        select(Opportunity)
        .where(Opportunity.company_id == identity.company_id)
    )

    if next_action is not None:
        stmt = stmt.where(Opportunity.next_action == next_action)

    if source is not None:
        stmt = stmt.where(Opportunity.source == source)

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            func.lower(Opportunity.title).like(func.lower(pattern)) |
            func.lower(Opportunity.description).like(func.lower(pattern))
        )

    if from_date:
        stmt = stmt.where(Opportunity.captured_at >= from_date)
    if to_date:
        stmt = stmt.where(Opportunity.captured_at <= to_date + "T23:59:59")

    stmt = stmt.order_by(Opportunity.id)
    opportunities = db.scalars(stmt).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "source", "title", "description", "budget", "deadline",
        "next_action", "outcome", "reason", "final_value",
        "captured_at", "created_at",
    ])

    for opp in opportunities:
        writer.writerow([
            opp.id,
            opp.source,
            opp.title,
            opp.description,
            opp.budget or "",
            opp.deadline or "",
            opp.next_action,
            opp.outcome or "",
            opp.reason or "",
            opp.final_value or "",
            opp.captured_at.isoformat() if opp.captured_at else "",
            opp.created_at.isoformat() if opp.created_at else "",
        ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=opportunities.csv",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get("/opportunities/count")
def count_opportunities(
    exclude_archived: bool = False,
    next_action: str | None = Query(None, description="Filter by next_action status"),
    source: str | None = Query(None, description="Filter by source"),
    q: str | None = Query(None, description="Search keywords in title and description"),
    from_date: str | None = Query(None, description="Filter captured_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter captured_at <= date (YYYY-MM-DD)"),
    lead_id: int | None = Query(None, description="Filter opportunities with conversations linked to this lead"),
    customer_id: int | None = Query(None, description="Filter opportunities with conversations linked to this customer"),
    priority_level: str | None = Query(None, description="Filter by priority level: high, medium, low"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Count opportunities with optional filters."""
    stmt = (
        select(func.count())
        .select_from(Opportunity)
        .where(Opportunity.company_id == identity.company_id)
    )

    if exclude_archived:
        stmt = stmt.where(Opportunity.next_action.notin_(["done", "lost"]))

    if next_action is not None:
        stmt = stmt.where(Opportunity.next_action == next_action)

    if source is not None:
        stmt = stmt.where(Opportunity.source == source)

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            func.lower(Opportunity.title).like(func.lower(pattern)) |
            func.lower(Opportunity.description).like(func.lower(pattern))
        )

    # WP-149 — date range filter
    if from_date:
        stmt = stmt.where(Opportunity.captured_at >= from_date)
    if to_date:
        stmt = stmt.where(Opportunity.captured_at <= to_date + "T23:59:59")

    # WP-263 — filter by lead_id or customer_id via conversations
    if lead_id is not None:
        stmt = stmt.where(
            exists().where(
                (Conversation.company_id == identity.company_id)
                & (Conversation.lead_id == lead_id)
            )
        )
    if customer_id is not None:
        stmt = stmt.where(
            exists().where(
                (Conversation.company_id == identity.company_id)
                & (Conversation.customer_id == customer_id)
            )
        )

    # WP-266 — if priority_level filter, count from list instead
    if priority_level is not None:
        opportunities = db.scalars(
            select(Opportunity).where(Opportunity.company_id == identity.company_id)
        ).all()
        if exclude_archived:
            opportunities = [o for o in opportunities if o.next_action not in ("done", "lost")]
        if next_action is not None:
            opportunities = [o for o in opportunities if o.next_action == next_action]
        if source is not None:
            opportunities = [o for o in opportunities if o.source == source]
        if q:
            pattern = f"%{q}%"
            opportunities = [
                o for o in opportunities
                if o.title.lower().find(q.lower()) >= 0 or (o.description or "").lower().find(q.lower()) >= 0
            ]
        if from_date:
            opportunities = [o for o in opportunities if o.captured_at and o.captured_at >= from_date]
        if to_date:
            opportunities = [o for o in opportunities if o.captured_at and o.captured_at <= to_date + "T23:59:59"]
        total = sum(
            1 for o in opportunities
            if _calculate_priority_score(o)["level"] == priority_level
        )
    else:
        total = db.scalar(stmt)
    return {"total": total}


@router.get("/opportunities/pipeline-summary")
def pipeline_summary(
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Return opportunity counts grouped by next_action (tenant-isolated)."""
    rows = db.execute(
        select(
            Opportunity.next_action,
            func.count(Opportunity.id),
        )
        .where(Opportunity.company_id == identity.company_id)
        .group_by(Opportunity.next_action)
    ).all()
    return {row[0]: row[1] for row in rows}


@router.get("/opportunities/export.csv")
def export_opportunities_csv(
    sort: str = Query(default="id", pattern="^(id|created_at|next_action|priority)$"),
    exclude_archived: bool = False,
    next_action: str | None = Query(None, description="Filter by next_action status"),
    source: str | None = Query(None, description="Filter by source"),
    q: str | None = Query(None, description="Search keywords in title and description"),
    from_date: str | None = Query(None, description="Filter captured_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter captured_at <= date (YYYY-MM-DD)"),
    lead_id: int | None = Query(None, description="Filter opportunities with conversations linked to this lead"),
    customer_id: int | None = Query(None, description="Filter opportunities with conversations linked to this customer"),
    priority_level: str | None = Query(None, description="Filter by priority level: high, medium, low"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Export tenant opportunities as a CSV file, respecting the same filters as the list."""
    stmt = (
        select(Opportunity)
        .where(Opportunity.company_id == identity.company_id)
    )

    if exclude_archived:
        stmt = stmt.where(Opportunity.next_action.notin_(["done", "lost"]))

    if next_action is not None:
        stmt = stmt.where(Opportunity.next_action == next_action)

    if source is not None:
        stmt = stmt.where(Opportunity.source == source)

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            func.lower(Opportunity.title).like(func.lower(pattern)) |
            func.lower(Opportunity.description).like(func.lower(pattern))
        )

    # WP-149 — date range filter
    if from_date:
        stmt = stmt.where(Opportunity.captured_at >= from_date)
    if to_date:
        stmt = stmt.where(Opportunity.captured_at <= to_date + "T23:59:59")

    # WP-263 — filter by lead_id or customer_id via conversations
    if lead_id is not None:
        stmt = stmt.where(
            exists().where(
                (Conversation.company_id == identity.company_id)
                & (Conversation.lead_id == lead_id)
            )
        )
    if customer_id is not None:
        stmt = stmt.where(
            exists().where(
                (Conversation.company_id == identity.company_id)
                & (Conversation.customer_id == customer_id)
            )
        )

    if sort == "created_at":
        stmt = stmt.order_by(desc(Opportunity.created_at), desc(Opportunity.id))
    elif sort == "next_action":
        stmt = stmt.order_by(Opportunity.next_action, Opportunity.id)
    else:
        stmt = stmt.order_by(Opportunity.id)
    opportunities = db.scalars(stmt).all()
    if sort == "priority":
        opportunities.sort(key=lambda opp: _calculate_priority_score(opp)["score"], reverse=True)

    # WP-266 — filter by priority level (computed in-memory)
    if priority_level is not None:
        opportunities = [
            opp for opp in opportunities
            if _calculate_priority_score(opp)["level"] == priority_level
        ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Titulo", "Descricao", "Status", "Orçamento",
        "Prazo", "Requisitos", "URL", "Fonte", "Nota triagem",
        "Capturada em", "Prioridade", "Nível prioridade",
    ])
    for opp in opportunities:
        priority = _calculate_priority_score(opp)
        writer.writerow([
            opp.id,
            opp.title,
            opp.description or "",
            opp.next_action or "",
            opp.budget or "",
            opp.deadline or "",
            opp.requirements or "",
            opp.external_url or "",
            opp.source or "",
            opp.triage_note or "",
            opp.captured_at.isoformat() if opp.captured_at else "",
            priority["score"],
            priority["level"],
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=opportunities.csv",
        },
    )


# WP-238 — Automatic priority score (must be before /opportunities/{opportunity_id})
def _calculate_priority_score(opp: Opportunity) -> dict:
    """Calculate a priority score (0-100) for an opportunity based on objective factors.

    Factors:
    - Deadline urgency: closer deadline = higher score (up to 40 points)
    - Budget presence: has budget = higher score (up to 20 points)
    - Status urgency: pending/follow = higher score (up to 25 points)
    - Source weight: intake/review_queue = higher score (up to 15 points)

    Returns a dict with score, level (high/medium/low) and factors breakdown.
    """
    from datetime import datetime

    score = 0
    factors = []

    # 1. Deadline urgency (0-40 points)
    if opp.deadline:
        try:
            deadline_date = datetime.fromisoformat(opp.deadline.replace("Z", "+00:00"))
            now = datetime.now(tz=deadline_date.tzinfo)
            days_until = (deadline_date - now).days

            if days_until <= 0:
                score += 40
                factors.append("Prazo expirado")
            elif days_until <= 7:
                score += 35
                factors.append(f"Prazo em {days_until} dias")
            elif days_until <= 14:
                score += 25
                factors.append(f"Prazo em {days_until} dias")
            elif days_until <= 30:
                score += 15
                factors.append(f"Prazo em {days_until} dias")
            else:
                score += 5
                factors.append(f"Prazo em {days_until} dias")
        except (ValueError, TypeError):
            pass
    else:
        score += 5
        factors.append("Sem prazo definido")

    # 2. Budget presence (0-20 points)
    if opp.budget:
        score += 20
        factors.append("Orçamento informado")
    else:
        factors.append("Sem orçamento")

    # 3. Status urgency (0-25 points)
    status_scores = {
        "pending": 25,
        "follow": 20,
        "prepare_proposal": 15,
        "in_progress": 10,
        "ignore": 5,
        "done": 0,
        "lost": 0,
    }
    status_score = status_scores.get(opp.next_action, 10)
    score += status_score
    factors.append(f"Status: {opp.next_action}")

    # 4. Source weight (0-15 points)
    source_scores = {
        "intake": 15,
        "review_queue": 15,
        "manual": 10,
        "import": 5,
        "99freelas": 10,
    }
    source_score = source_scores.get(opp.source, 5)
    score += source_score
    factors.append(f"Fonte: {opp.source}")

    # Determine level
    if score >= 70:
        level = "high"
    elif score >= 40:
        level = "medium"
    else:
        level = "low"

    return {
        "score": min(score, 100),
        "level": level,
        "factors": factors,
    }


@router.get("/opportunities/priority")
def get_priority_opportunities(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Return opportunities ordered by calculated priority score (descending).

    The priority score is computed on-the-fly from deadline, budget, status
    and source — no database migration required.
    """
    stmt = (
        select(Opportunity)
        .where(Opportunity.company_id == identity.company_id)
        .order_by(Opportunity.id)
    )
    opportunities = db.scalars(stmt).all()

    # Calculate scores and sort
    scored = []
    for opp in opportunities:
        priority = _calculate_priority_score(opp)
        scored.append({
            "id": opp.id,
            "title": opp.title,
            "next_action": opp.next_action,
            "deadline": opp.deadline,
            "budget": opp.budget,
            "source": opp.source,
            "priority_score": priority["score"],
            "priority_level": priority["level"],
            "priority_factors": priority["factors"],
        })

    scored.sort(key=lambda x: x["priority_score"], reverse=True)
    return scored[:limit]


@router.get("/opportunities/stale", response_model=StaleOpportunitiesResponse)
def get_stale_opportunities(
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
    stale_days: int = Query(14, ge=1),
):
    """Find opportunities that have been inactive for a configurable period."""
    from app.services.followup import find_stale_opportunities

    stale = find_stale_opportunities(
        db,
        identity.company_id,
        stale_days=stale_days,
    )
    return StaleOpportunitiesResponse(
        opportunities=[
            StaleOpportunityResponse(
                opportunity_id=s.opportunity_id,
                title=s.title,
                days_since_activity=s.days_since_activity,
                next_action=s.next_action,
            )
            for s in stale
        ]
    )


@router.get("/opportunities/{opportunity_id}")
def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )


@router.get("/opportunities/{opportunity_id}/conversations")
def get_opportunity_conversations(
    opportunity_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Return conversations belonging to the same company as the opportunity (tenant-isolated)."""
    _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )
    from app.models import Conversation
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.company_id == identity.company_id)
        .order_by(desc(Conversation.id))
        .limit(50)
    ).all()
    return conversations


@router.get("/opportunities/{opportunity_id}/leads")
def get_opportunity_leads(
    opportunity_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Return leads belonging to the same company as the opportunity (tenant-isolated)."""
    _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )
    from app.models import Lead
    leads = db.scalars(
        select(Lead)
        .where(Lead.company_id == identity.company_id)
        .order_by(desc(Lead.id))
        .limit(50)
    ).all()
    return leads


@router.get("/opportunities/{opportunity_id}/linked-conversations")
def get_opportunity_linked_conversations(
    opportunity_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Return conversations for the opportunity's explicit lead or customer."""
    opportunity = _get_tenant_opportunity(db, opportunity_id, identity.company_id)
    if opportunity.lead_id is None and opportunity.customer_id is None:
        return []
    predicate = (
        Conversation.lead_id == opportunity.lead_id
        if opportunity.lead_id is not None
        else Conversation.customer_id == opportunity.customer_id
    )
    return db.scalars(select(Conversation).where(
        Conversation.company_id == identity.company_id,
        predicate,
    ).order_by(desc(Conversation.id)).limit(50)).all()


@router.get("/opportunities/{opportunity_id}/linked-leads")
def get_opportunity_linked_leads(
    opportunity_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Return only the lead explicitly linked to this opportunity."""
    opportunity = _get_tenant_opportunity(db, opportunity_id, identity.company_id)
    if opportunity.lead_id is None:
        return []
    lead = db.scalar(select(Lead).where(
        Lead.id == opportunity.lead_id,
        Lead.company_id == identity.company_id,
    ))
    return [] if lead is None else [lead]


@router.get("/opportunities/{opportunity_id}/linked-customers")
def get_opportunity_linked_customers(
    opportunity_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Return only the customer explicitly linked to this opportunity."""
    opportunity = _get_tenant_opportunity(db, opportunity_id, identity.company_id)
    if opportunity.customer_id is None:
        return []
    customer = db.scalar(select(Customer).where(
        Customer.id == opportunity.customer_id,
        Customer.company_id == identity.company_id,
    ))
    return [] if customer is None else [customer]


@router.get("/opportunities/{opportunity_id}/timeline")
def get_opportunity_timeline(
    opportunity_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Return an activity timeline for the opportunity derived from existing data.

    Events include: creation, triage changes, brief status changes.
    No migration required — all data comes from existing models.
    """
    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    events = []

    # Creation event
    events.append({
        "type": "created",
        "timestamp": opportunity.created_at.isoformat(),
        "detail": f"Oportunidade capturada da fonte '{opportunity.source}'",
    })

    # Triage event if triage_note exists
    if opportunity.triage_note:
        events.append({
            "type": "triage",
            "timestamp": opportunity.updated_at.isoformat(),
            "detail": f"Triagem: {opportunity.next_action} — {opportunity.triage_note}",
        })

    # Brief events
    brief = db.scalar(
        select(ProposalBrief).where(
            ProposalBrief.opportunity_id == opportunity_id,
        )
    )
    if brief is not None:
        events.append({
            "type": "brief_created",
            "timestamp": brief.created_at.isoformat(),
            "detail": f"ProposalBrief criado ({brief.offer_reference})",
        })
        if brief.status != "draft":
            events.append({
                "type": "brief_status",
                "timestamp": brief.updated_at.isoformat(),
                "detail": f"ProposalBrief → {brief.status}",
            })

    # Sort by timestamp descending
    events.sort(key=lambda e: e["timestamp"], reverse=True)

    return events


@router.patch("/opportunities/{opportunity_id}")
def update_opportunity(
    opportunity_id: int,
    data: OpportunityUpdate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Update opportunity title, description and/or triage note (tenant-isolated)."""
    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    changed = data.model_dump(exclude_unset=True)
    if not changed:
        raise HTTPException(
            status_code=400,
            detail="No fields to update",
        )

    if "title" in changed:
        opportunity.title = changed["title"]
    if "description" in changed:
        opportunity.description = changed["description"]
    if "triage_note" in changed:
        opportunity.triage_note = changed["triage_note"]
    if "lead_id" in changed and "customer_id" in changed:
        raise HTTPException(status_code=400, detail="opportunity cannot belong to both lead and customer")
    if "lead_id" in changed:
        if changed["lead_id"] is not None and db.scalar(select(Lead.id).where(
            Lead.id == changed["lead_id"], Lead.company_id == identity.company_id,
        )) is None:
            raise HTTPException(status_code=404, detail="Lead not found")
        opportunity.lead_id = changed["lead_id"]
        if changed["lead_id"] is not None:
            opportunity.customer_id = None
    if "customer_id" in changed:
        if changed["customer_id"] is not None and db.scalar(select(Customer.id).where(
            Customer.id == changed["customer_id"], Customer.company_id == identity.company_id,
        )) is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        opportunity.customer_id = changed["customer_id"]
        if changed["customer_id"] is not None:
            opportunity.lead_id = None

    db.commit()
    db.refresh(opportunity)

    return opportunity


# Valid status transitions for the F2 commercial cycle
# Note: new opportunities default to "pending" in the model
_VALID_TRANSITIONS = {
    "pending": {"ignore", "follow", "prepare_proposal", "in_progress"},
    "ignore": set(),  # terminal state
    "follow": {"pending", "ignore", "prepare_proposal", "in_progress"},
    "prepare_proposal": {"pending", "follow", "in_progress"},
    "in_progress": {"done", "lost"},
    "done": set(),  # terminal state
    "lost": set(),  # terminal state
}


@router.patch("/opportunities/{opportunity_id}/close")
def close_opportunity(
    opportunity_id: int,
    data: OpportunityClose,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Close an opportunity as won or lost with optional reason and final value.

    Sets outcome, reason, final_value, and closed_at.  Also advances
    next_action to 'done' (won) or 'lost' so the pipeline reflects the
    final state.
    """
    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    if opportunity.outcome is not None:
        raise HTTPException(
            status_code=400,
            detail="Opportunity is already closed",
        )

    opportunity.outcome = data.outcome
    opportunity.reason = data.reason
    opportunity.final_value = data.final_value
    opportunity.closed_at = datetime.now(timezone.utc)
    opportunity.next_action = "done" if data.outcome == "won" else "lost"

    db.commit()
    db.refresh(opportunity)

    return opportunity


@router.patch("/opportunities/{opportunity_id}/triage")
def triage_opportunity(
    opportunity_id: int,
    data: OpportunityTriageUpdate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    current = opportunity.next_action
    allowed = _VALID_TRANSITIONS.get(current, set())
    if data.next_action not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{current}' to '{data.next_action}'",
        )

    opportunity.next_action = data.next_action
    opportunity.triage_note = data.triage_note

    db.commit()
    db.refresh(opportunity)

    return opportunity


@router.post("/opportunities/bulk-triage")
def bulk_triage_opportunities(
    data: OpportunityBulkTriage,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Apply the same triage action to multiple opportunities at once.

    Only opportunities belonging to the authenticated tenant are updated.
    Opportunities that don't exist, belong to another tenant, or have
    invalid transitions are skipped. The response includes counts of
    updated and skipped opportunities.
    """
    opportunities = db.scalars(
        select(Opportunity).where(
            Opportunity.id.in_(data.opportunity_ids),
            Opportunity.company_id == identity.company_id,
        )
    ).all()

    updated_ids = []
    base_skipped = len(data.opportunity_ids) - len(opportunities)

    for opportunity in opportunities:
        current = opportunity.next_action
        allowed = _VALID_TRANSITIONS.get(current, set())
        if data.next_action not in allowed:
            continue
        opportunity.next_action = data.next_action
        opportunity.triage_note = data.triage_note
        updated_ids.append(opportunity.id)

    db.commit()

    return {
        "updated": len(updated_ids),
        "updated_ids": updated_ids,
        "skipped": base_skipped + len(opportunities) - len(updated_ids),
        "next_action": data.next_action,
    }


def _get_proposal_brief(
    db: Session,
    opportunity_id: int,
) -> ProposalBrief:
    brief = db.scalar(
        select(ProposalBrief).where(
            ProposalBrief.opportunity_id == opportunity_id,
        )
    )

    if brief is None:
        raise HTTPException(
            status_code=404,
            detail="Proposal brief not found",
        )

    return brief


def _proposal_brief_exists(
    db: Session,
    opportunity_id: int,
) -> bool:
    return (
        db.scalar(
            select(ProposalBrief.id).where(
                ProposalBrief.opportunity_id == opportunity_id,
            )
        )
        is not None
    )


@router.post("/opportunities/{opportunity_id}/proposal-brief")
def create_proposal_brief(
    opportunity_id: int,
    data: ProposalBriefCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    if opportunity.next_action != "prepare_proposal":
        raise HTTPException(
            status_code=409,
            detail="Opportunity is not ready for proposal preparation",
        )

    if _proposal_brief_exists(db, opportunity.id):
        raise HTTPException(
            status_code=409,
            detail="Proposal brief already exists",
        )

    brief = ProposalBrief(
        opportunity_id=opportunity.id,
        offer_reference=data.offer_reference,
        diagnosis=data.diagnosis,
        scope=data.scope,
        deliverables=data.deliverables,
        acceptance_criteria=data.acceptance_criteria,
        assumptions=data.assumptions,
        risks=data.risks,
        status="draft",
    )

    db.add(brief)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        if _proposal_brief_exists(db, opportunity.id):
            raise HTTPException(
                status_code=409,
                detail="Proposal brief already exists",
            )

        raise

    db.refresh(brief)
    return brief


@router.get("/opportunities/{opportunity_id}/proposal-brief")
def get_proposal_brief(
    opportunity_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    return _get_proposal_brief(
        db,
        opportunity.id,
    )


@router.patch("/opportunities/{opportunity_id}/proposal-brief")
def update_proposal_brief(
    opportunity_id: int,
    data: ProposalBriefUpdate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Partially update a proposal brief. Only non-null fields are modified."""
    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    brief = _get_proposal_brief(
        db,
        opportunity.id,
    )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(brief, key, value)

    db.commit()
    db.refresh(brief)

    return brief


@router.patch("/opportunities/{opportunity_id}/proposal-brief/approve")
def approve_proposal_brief(
    opportunity_id: int,
    data: ProposalBriefDecision | None = None,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Approve a proposal brief and advance the opportunity to in_progress.

    Atomic operation: updates both brief status and opportunity next_action.
    Only accepts briefs that are 'ready_for_review'.
    Optional operator_note is preserved for audit trail.
    """
    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    brief = _get_proposal_brief(
        db,
        opportunity.id,
    )

    if brief.status != "ready_for_review":
        raise HTTPException(
            status_code=400,
            detail="Brief must be 'ready_for_review' to approve",
        )

    brief.status = "approved"
    if data is not None and data.operator_note is not None:
        brief.operator_note = data.operator_note
    brief.decided_at = datetime.now(timezone.utc)
    opportunity.next_action = "in_progress"

    db.commit()
    db.refresh(brief)

    return brief


@router.patch("/opportunities/{opportunity_id}/proposal-brief/reject")
def reject_proposal_brief(
    opportunity_id: int,
    data: ProposalBriefDecision | None = None,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Reject a proposal brief, reverting it to draft.

    Only accepts briefs that are 'approved' or 'ready_for_review'.
    Does not change the opportunity next_action.
    Optional operator_note is preserved for audit trail.
    """
    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    brief = _get_proposal_brief(
        db,
        opportunity.id,
    )

    if brief.status not in ("approved", "ready_for_review"):
        raise HTTPException(
            status_code=400,
            detail="Brief must be 'approved' or 'ready_for_review' to reject",
        )

    brief.status = "draft"
    if data is not None and data.operator_note is not None:
        brief.operator_note = data.operator_note
    brief.decided_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(brief)

    return brief


@router.patch("/proposal-briefs/{brief_id}/decision")
def decide_proposal_brief(
    brief_id: int,
    data: ProposalBriefDecision,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Unified decision endpoint for a proposal brief.

    Approves or rejects the brief in a single call, recording the operator
    note and decision timestamp.  The brief must belong to the authenticated
    tenant (via its opportunity).
    """
    brief = db.scalar(
        select(ProposalBrief)
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(
            ProposalBrief.id == brief_id,
            Opportunity.company_id == identity.company_id,
        )
    )

    if brief is None:
        raise HTTPException(
            status_code=404,
            detail="Brief not found",
        )

    now = datetime.now(timezone.utc)

    if data.decision == "approve":
        if brief.status != "ready_for_review":
            raise HTTPException(
                status_code=400,
                detail="Brief must be 'ready_for_review' to approve",
            )
        brief.status = "approved"
        opportunity = db.scalar(
            select(Opportunity).where(Opportunity.id == brief.opportunity_id)
        )
        if opportunity is not None:
            opportunity.next_action = "in_progress"
    else:
        # reject
        if brief.status not in ("approved", "ready_for_review"):
            raise HTTPException(
                status_code=400,
                detail="Brief must be 'approved' or 'ready_for_review' to reject",
            )
        brief.status = "draft"

    if data.operator_note is not None:
        brief.operator_note = data.operator_note
    brief.decided_at = now

    db.commit()
    db.refresh(brief)

    return brief


# ---------------------------------------------------------------------------
# WP-178 — Brief list view (tenant-isolated)
# ---------------------------------------------------------------------------


@router.get("/proposal-briefs")
def list_proposal_briefs(
    status: str | None = Query(default=None, description="Filter by brief status"),
    q: str | None = Query(default=None, description="Search keywords in title and offer reference"),
    opportunity_id: int | None = Query(default=None, description="Filter by opportunity"),
    from_date: str | None = Query(default=None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(default=None, description="Filter created_at <= date (YYYY-MM-DD)"),
    sort: str = Query(default="created_at", description="Sort by: created_at, id, status, title"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """List all proposal briefs for the authenticated tenant company.

    Returns briefs joined with opportunity data for context.
    """
    query = (
        select(
            ProposalBrief.id,
            ProposalBrief.opportunity_id,
            ProposalBrief.offer_reference,
            ProposalBrief.status,
            ProposalBrief.created_at,
            Opportunity.title.label("opportunity_title"),
        )
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(Opportunity.company_id == identity.company_id)
    )

    if status:
        query = query.where(ProposalBrief.status == status)

    if opportunity_id is not None:
        query = query.where(ProposalBrief.opportunity_id == opportunity_id)

    if q:
        pattern = f"%{q}%"
        query = query.where(
            func.lower(Opportunity.title).like(func.lower(pattern)) |
            func.lower(ProposalBrief.offer_reference).like(func.lower(pattern))
        )

    if from_date:
        query = query.where(ProposalBrief.created_at >= from_date)
    if to_date:
        query = query.where(ProposalBrief.created_at <= to_date + "T23:59:59")

    if sort == "created_at":
        query = query.order_by(desc(ProposalBrief.created_at), desc(ProposalBrief.id))
    elif sort == "status":
        query = query.order_by(ProposalBrief.status, ProposalBrief.id)
    elif sort == "title":
        query = query.order_by(Opportunity.title, ProposalBrief.id)
    else:
        query = query.order_by(ProposalBrief.id)

    query = query.offset(offset).limit(limit)
    rows = db.execute(query).all()
    return [
        {
            "id": row.id,
            "opportunity_id": row.opportunity_id,
            "opportunity_title": row.opportunity_title,
            "offer_reference": row.offer_reference,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/proposal-briefs/count")
def count_proposal_briefs(
    status: str | None = Query(default=None, description="Filter by brief status"),
    q: str | None = Query(default=None, description="Search keywords in title and offer reference"),
    opportunity_id: int | None = Query(default=None, description="Filter by opportunity"),
    from_date: str | None = Query(default=None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(default=None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Count proposal briefs for the authenticated tenant company."""
    query = (
        select(func.count())
        .select_from(ProposalBrief)
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(Opportunity.company_id == identity.company_id)
    )

    if status:
        query = query.where(ProposalBrief.status == status)

    if opportunity_id is not None:
        query = query.where(ProposalBrief.opportunity_id == opportunity_id)

    if q:
        pattern = f"%{q}%"
        query = query.where(
            func.lower(Opportunity.title).like(func.lower(pattern)) |
            func.lower(ProposalBrief.offer_reference).like(func.lower(pattern))
        )

    if from_date:
        query = query.where(ProposalBrief.created_at >= from_date)
    if to_date:
        query = query.where(ProposalBrief.created_at <= to_date + "T23:59:59")

    count = db.execute(query).scalar_one()
    return {"count": count}


@router.get("/proposal-briefs/export.csv")
def export_briefs_csv(
    sort: str = Query(default="id", pattern="^(id|created_at|status|title)$"),
    status: str | None = Query(default=None, description="Filter by brief status"),
    q: str | None = Query(default=None, description="Search keywords in title and offer reference"),
    opportunity_id: int | None = Query(default=None, description="Filter by opportunity"),
    from_date: str | None = Query(default=None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(default=None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Export proposal briefs for the authenticated tenant as CSV, respecting filters.

    WP-250: Includes all detailed fields (diagnosis, scope, deliverables, etc).
    """
    query = (
        select(
            ProposalBrief.id,
            ProposalBrief.opportunity_id,
            ProposalBrief.offer_reference,
            ProposalBrief.diagnosis,
            ProposalBrief.scope,
            ProposalBrief.deliverables,
            ProposalBrief.acceptance_criteria,
            ProposalBrief.assumptions,
            ProposalBrief.risks,
            ProposalBrief.status,
            ProposalBrief.created_at,
            Opportunity.title.label("opportunity_title"),
        )
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(Opportunity.company_id == identity.company_id)
    )

    if status:
        query = query.where(ProposalBrief.status == status)

    if opportunity_id is not None:
        query = query.where(ProposalBrief.opportunity_id == opportunity_id)

    if q:
        pattern = f"%{q}%"
        query = query.where(
            func.lower(Opportunity.title).like(func.lower(pattern)) |
            func.lower(ProposalBrief.offer_reference).like(func.lower(pattern))
        )

    if from_date:
        query = query.where(ProposalBrief.created_at >= from_date)
    if to_date:
        query = query.where(ProposalBrief.created_at <= to_date + "T23:59:59")

    if sort == "created_at":
        query = query.order_by(desc(ProposalBrief.created_at), desc(ProposalBrief.id))
    elif sort == "status":
        query = query.order_by(ProposalBrief.status, ProposalBrief.id)
    elif sort == "title":
        query = query.order_by(Opportunity.title, ProposalBrief.id)
    else:
        query = query.order_by(ProposalBrief.id)

    rows = db.execute(query).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Oportunidade ID", "Título", "Referência", "Diagnóstico",
        "Escopo", "Entregáveis", "Critérios", "Hipóteses", "Riscos",
        "Status", "Criada em",
    ])
    for row in rows:
        writer.writerow([
            row.id,
            row.opportunity_id,
            row.opportunity_title or "",
            row.offer_reference or "",
            row.diagnosis or "",
            row.scope or "",
            row.deliverables or "",
            row.acceptance_criteria or "",
            row.assumptions or "",
            row.risks or "",
            row.status,
            row.created_at.isoformat() if row.created_at else "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=proposal-briefs.csv",
        },
    )


# ---------------------------------------------------------------------------
# WP-187 — Get single brief detail (tenant-isolated)
# Placed after static paths (/count, /export.csv) to avoid route conflict.
# ---------------------------------------------------------------------------


@router.get("/proposal-briefs/{brief_id}/conversations")
def get_brief_conversations(
    brief_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Get conversations related to the brief's opportunity (tenant-isolated)."""
    brief = db.execute(
        select(ProposalBrief)
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(
            ProposalBrief.id == brief_id,
            Opportunity.company_id == identity.company_id,
        )
    ).scalar_one_or_none()

    if brief is None:
        raise HTTPException(status_code=404, detail="Brief não encontrado")

    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.company_id == identity.company_id)
        .order_by(Conversation.id)
        .limit(50)
    ).all()

    return [
        {
            "id": c.id,
            "channel": c.channel,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in conversations
    ]


@router.get("/proposal-briefs/{brief_id}")
def get_proposal_brief(
    brief_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Get a single proposal brief with all fields (tenant-isolated)."""
    brief = db.execute(
        select(ProposalBrief)
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(
            ProposalBrief.id == brief_id,
            Opportunity.company_id == identity.company_id,
        )
    ).scalar_one_or_none()

    if brief is None:
        raise HTTPException(status_code=404, detail="Brief não encontrado")

    return {
        "id": brief.id,
        "opportunity_id": brief.opportunity_id,
        "offer_reference": brief.offer_reference,
        "diagnosis": brief.diagnosis,
        "scope": brief.scope,
        "deliverables": brief.deliverables,
        "acceptance_criteria": brief.acceptance_criteria,
        "status": brief.status,
        "created_at": brief.created_at.isoformat() if brief.created_at else None,
    }


# ---------------------------------------------------------------------------
# WP-180 — Bulk delete opportunities
# ---------------------------------------------------------------------------


@router.post("/opportunities/bulk-delete")
def bulk_delete_opportunities(
    data: OpportunityBulkDelete,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Bulk delete multiple opportunities (tenant-isolated)."""
    opportunities = db.scalars(
        select(Opportunity).where(
            Opportunity.id.in_(data.opportunity_ids),
            Opportunity.company_id == identity.company_id,
        )
    ).all()

    deleted_ids = []
    for opp in opportunities:
        db.delete(opp)
        deleted_ids.append(opp.id)

    db.commit()

    skipped = set(data.opportunity_ids) - set(deleted_ids)

    return {
        "deleted": len(deleted_ids),
        "deleted_ids": sorted(deleted_ids),
        "skipped": sorted(skipped),
    }


# ---------------------------------------------------------------------------
# WP-184 — Bulk status update for proposal briefs
# ---------------------------------------------------------------------------


@router.post("/proposal-briefs/bulk-status")
def bulk_update_brief_status(
    data: ProposalBriefBulkStatus,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Bulk update status for multiple proposal briefs (tenant-isolated)."""
    briefs = db.scalars(
        select(ProposalBrief)
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(
            ProposalBrief.id.in_(data.brief_ids),
            Opportunity.company_id == identity.company_id,
        )
    ).all()

    updated_ids = []
    for brief in briefs:
        brief.status = data.status
        updated_ids.append(brief.id)

    db.commit()

    skipped = set(data.brief_ids) - set(updated_ids)

    return {
        "updated": len(updated_ids),
        "updated_ids": sorted(updated_ids),
        "skipped": sorted(skipped),
    }


# ---------------------------------------------------------------------------
# WP-185 — Bulk delete proposal briefs
# ---------------------------------------------------------------------------


@router.post("/proposal-briefs/bulk-delete")
def bulk_delete_briefs(
    data: ProposalBriefBulkDelete,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Bulk delete multiple proposal briefs (tenant-isolated)."""
    briefs = db.scalars(
        select(ProposalBrief)
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(
            ProposalBrief.id.in_(data.brief_ids),
            Opportunity.company_id == identity.company_id,
        )
    ).all()

    deleted_ids = []
    for brief in briefs:
        db.delete(brief)
        deleted_ids.append(brief.id)

    db.commit()

    skipped = set(data.brief_ids) - set(deleted_ids)

    return {
        "deleted": len(deleted_ids),
        "deleted_ids": sorted(deleted_ids),
        "skipped": sorted(skipped),
    }


# ---------------------------------------------------------------------------
# WP-237 — AI-assisted triage suggestion
# ---------------------------------------------------------------------------


_TRIAGE_SYSTEM_PROMPT = (
    "Você é um assistente de triagem comercial. "
    "Analise a oportunidade abaixo e sugira a próxima ação. "
    "Responda APENAS com um JSON no formato: "
    '{"action": "<next_action>", "reasoning": "<breve justificativa>", "confidence": <0.0-1.0>}. '
    "As opções de action são: pending, ignore, follow, prepare_proposal, in_progress, done, lost. "
    "Não inclua nada além do JSON."
)


def _build_triage_prompt(opp: Opportunity) -> str:
    """Build the user prompt for triage suggestion based on opportunity context."""
    parts = [
        f"Título: {opp.title}",
        f"Descrição: {opp.description or '(vazia)'}",
        f"Orçamento: {opp.budget or '(não informado)'}",
        f"Prazo: {opp.deadline or '(não informado)'}",
        f"Requisitos: {opp.requirements or '(não informados)'}",
        f"Fonte: {opp.source or '(desconhecida)'}",
        f"Status atual: {opp.next_action}",
        f"Nota de triagem: {opp.triage_note or '(nenhuma)'}",
    ]
    return "\n".join(parts)


@router.post("/opportunities/{opportunity_id}/suggest-triage")
def suggest_triage(
    opportunity_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Suggest the next triage action for an opportunity using AI.

    This endpoint does NOT persist the suggestion — it returns the AI's
    recommendation so the operator can review and apply it manually.
    Returns 503 if the agent service is unavailable.
    """
    from app.services.agent import AgentServiceError, generate_agent_reply

    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    # Load company agent config for defaults
    from app.routers.companies import _agent_config_store
    config = _agent_config_store.get(identity.company_id)
    system_prompt = (config.get("system_prompt") if config else None) or _TRIAGE_SYSTEM_PROMPT
    temperature = config.get("temperature") if config else None
    max_tokens = config.get("max_tokens") if config else None
    model = config.get("model") if config else None

    prompt = _build_triage_prompt(opportunity)

    try:
        reply = generate_agent_reply(
            message=prompt,
            history=[],
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
    except AgentServiceError:
        raise HTTPException(
            status_code=503,
            detail="Serviço de agente indisponível",
        )

    # Parse JSON response from agent
    import json as json_module

    try:
        data = json_module.loads(reply)
        action = data.get("action", "pending")
        reasoning = data.get("reasoning", "Sem justificativa")
        confidence = data.get("confidence")
    except (json_module.JSONDecodeError, AttributeError):
        return {
            "suggested_action": "pending",
            "reasoning": reply[:500] if isinstance(reply, str) else str(reply)[:500],
            "confidence": None,
            "raw_response": reply,
        }

    valid_actions = {"pending", "ignore", "follow", "prepare_proposal", "in_progress", "done", "lost"}
    if action not in valid_actions:
        action = "pending"

    return {
        "suggested_action": action,
        "reasoning": reasoning,
        "confidence": confidence,
    }


@router.post("/opportunities/bulk-suggest-triage", response_model=OpportunityBulkTriageSuggestionResponse)
def bulk_suggest_triage(
    data: OpportunityBulkTriageSuggestion,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Suggest the best triage action for a group of selected opportunities using AI.

    Analyzes all selected opportunities and returns a single suggested action
    that applies to the majority, along with reasoning and matching count.
    Returns 503 if the agent service is unavailable.
    """
    from app.services.agent import AgentServiceError, generate_agent_reply

    # Fetch tenant-isolated opportunities
    opportunities = db.scalars(
        select(Opportunity).where(
            Opportunity.id.in_(data.opportunity_ids),
            Opportunity.company_id == identity.company_id,
        )
    ).all()

    if not opportunities:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma oportunidade encontrada",
        )

    total_count = len(opportunities)

    # Build a combined prompt with all opportunity summaries
    summaries = []
    for opp in opportunities:
        summaries.append(
            f"#{opp.id}: {opp.title} | Status: {opp.next_action} | "
            f"Prazo: {opp.deadline or '(nenhum)'} | "
            f"Orçamento: {opp.budget or '(nenhum)'} | "
            f"Fonte: {opp.source or '(desconhecida)'}"
        )
    prompt = (
        f"Analise estas {total_count} oportunidades e sugira a melhor ação de triagem "
        f"que se aplica à maioria:\n\n"
        + "\n".join(summaries)
    )

    # Load company agent config for defaults
    from app.routers.companies import _agent_config_store
    config = _agent_config_store.get(identity.company_id)
    system_prompt = (config.get("system_prompt") if config else None) or _TRIAGE_SYSTEM_PROMPT
    temperature = config.get("temperature") if config else None
    max_tokens = config.get("max_tokens") if config else None
    model = config.get("model") if config else None

    try:
        reply = generate_agent_reply(
            message=prompt,
            history=[],
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
    except AgentServiceError:
        raise HTTPException(
            status_code=503,
            detail="Serviço de agente indisponível",
        )

    # Parse JSON response from agent
    import json as json_module

    try:
        parsed = json_module.loads(reply)
        action = parsed.get("action", "pending")
        reasoning = parsed.get("reasoning", "Sem justificativa")
        matching = parsed.get("matching_count", total_count)
    except (json_module.JSONDecodeError, AttributeError):
        return {
            "suggested_action": "pending",
            "reasoning": reply[:500] if isinstance(reply, str) else str(reply)[:500],
            "matching_count": total_count,
            "total_count": total_count,
        }

    valid_actions = {"pending", "ignore", "follow", "prepare_proposal", "in_progress", "done", "lost"}
    if action not in valid_actions:
        action = "pending"

    # Count how many opportunities can actually transition to the suggested action
    matching_count = 0
    for opp in opportunities:
        allowed = _VALID_TRANSITIONS.get(opp.next_action, set())
        if action in allowed:
            matching_count += 1

    return {
        "suggested_action": action,
        "reasoning": reasoning,
        "matching_count": matching_count,
        "total_count": total_count,
    }


# ---------------------------------------------------------------------------
# WP-240 — AI-assisted proposal brief suggestion
# ---------------------------------------------------------------------------


_BRIEF_SYSTEM_PROMPT = (
    "Voce e um assistente para criar rascunhos de proposta comercial. "
    "Analise a oportunidade abaixo e gere um rascunho de proposal brief. "
    "Responda APENAS com um JSON no formato: "
    '{"offer_reference": "<titulo curto>", "diagnosis": "<diagnostico do problema>", '
    '"scope": "<escopo da solucao>", "deliverables": "<entregaveis>", '
    '"acceptance_criteria": "<critérios de aceitação>", "assumptions": "<suposicoes>", '
    '"risks": "<riscos>"}. '
    "Nao inclua nada alem do JSON. Seja conciso e pratico."
)


def _build_brief_prompt(opp: Opportunity) -> str:
    """Build the user prompt for brief suggestion based on opportunity context."""
    parts = [
        f"Titulo: {opp.title}",
        f"Descricao: {opp.description or '(vazia)'}",
        f"Orcamento: {opp.budget or '(nao informado)'}",
        f"Prazo: {opp.deadline or '(nao informado)'}",
        f"Requisitos: {opp.requirements or '(nao informados)'}",
        f"Fonte: {opp.source or '(desconhecida)'}",
        f"Nota de triagem: {opp.triage_note or '(nenhuma)'}",
    ]
    return "\n".join(parts)


@router.post("/opportunities/{opportunity_id}/suggest-brief", response_model=ProposalBriefSuggestion)
def suggest_brief(
    opportunity_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Suggest proposal brief content for an opportunity using AI.

    This endpoint does NOT persist the suggestion — it returns the AI's
    draft so the operator can review and edit before creating the brief.
    Returns 503 if the agent service is unavailable.
    """
    from app.services.agent import AgentServiceError, generate_agent_reply

    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    # Load company agent config for defaults
    from app.routers.companies import _agent_config_store
    config = _agent_config_store.get(identity.company_id)
    system_prompt = (config.get("system_prompt") if config else None) or _BRIEF_SYSTEM_PROMPT
    temperature = config.get("temperature") if config else None
    max_tokens = config.get("max_tokens") if config else None
    model = config.get("model") if config else None

    prompt = _build_brief_prompt(opportunity)

    try:
        reply = generate_agent_reply(
            message=prompt,
            history=[],
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
    except AgentServiceError:
        raise HTTPException(
            status_code=503,
            detail="Servico de agente indisponivel",
        )

    # Parse JSON response from agent
    import json as json_module

    try:
        data = json_module.loads(reply)
        return ProposalBriefSuggestion(
            offer_reference=data.get("offer_reference", opportunity.title),
            diagnosis=data.get("diagnosis", ""),
            scope=data.get("scope", ""),
            deliverables=data.get("deliverables", ""),
            acceptance_criteria=data.get("acceptance_criteria", ""),
            assumptions=data.get("assumptions"),
            risks=data.get("risks"),
        )
    except (json_module.JSONDecodeError, AttributeError):
        # Fallback: return raw response as diagnosis
        return ProposalBriefSuggestion(
            offer_reference=opportunity.title,
            diagnosis=reply[:2000] if isinstance(reply, str) else str(reply)[:2000],
            scope="",
            deliverables="",
            acceptance_criteria="",
        )


@router.patch("/opportunities/{opportunity_id}/favorite")
def toggle_opportunity_favorite(
    opportunity_id: int,
    data: FavoriteToggle,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Toggle favorite status for an opportunity."""
    opportunity = _get_tenant_opportunity(db, opportunity_id, identity.company_id)

    key = (identity.company_id, "opportunity", opportunity_id)
    if data.favorited:
        from datetime import datetime, timezone
        _favorites_store[key] = {"favorited_at": datetime.now(timezone.utc)}
    else:
        _favorites_store.pop(key, None)

    favorited_at = _favorites_store.get(key, {}).get("favorited_at")
    return FavoriteResponse(
        entity_type="opportunity",
        entity_id=opportunity_id,
        favorited=data.favorited,
        favorited_at=favorited_at,
    )
