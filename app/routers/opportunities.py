import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, require_operator
from app.models import Company, Conversation, Opportunity, ProposalBrief
from app.schemas import (
    OpportunityBulkDelete,
    OpportunityBulkTriage,
    OpportunityCreate,
    OpportunityTriageUpdate,
    OpportunityUpdate,
    ProposalBriefBulkDelete,
    ProposalBriefBulkStatus,
    ProposalBriefCreate,
    ProposalBriefUpdate,
)


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
        next_action="pending",
    )

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
    q: str | None = Query(None, description="Search keywords in title and description"),
    from_date: str | None = Query(None, description="Filter captured_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter captured_at <= date (YYYY-MM-DD)"),
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

    if sort == "created_at":
        stmt = stmt.order_by(desc(Opportunity.created_at), desc(Opportunity.id))
    elif sort == "next_action":
        stmt = stmt.order_by(Opportunity.next_action, Opportunity.id)
    else:
        stmt = stmt.order_by(Opportunity.id)

    stmt = stmt.offset(offset).limit(limit)
    return db.scalars(stmt).all()


@router.get("/opportunities/count")
def count_opportunities(
    exclude_archived: bool = False,
    next_action: str | None = Query(None, description="Filter by next_action status"),
    q: str | None = Query(None, description="Search keywords in title and description"),
    from_date: str | None = Query(None, description="Filter captured_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter captured_at <= date (YYYY-MM-DD)"),
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
    exclude_archived: bool = False,
    next_action: str | None = Query(None, description="Filter by next_action status"),
    q: str | None = Query(None, description="Search keywords in title and description"),
    from_date: str | None = Query(None, description="Filter captured_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter captured_at <= date (YYYY-MM-DD)"),
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

    stmt = stmt.order_by(Opportunity.id)
    opportunities = db.scalars(stmt).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Titulo", "Descricao", "Status", "Orçamento",
        "Prazo", "Requisitos", "URL", "Fonte", "Nota triagem",
        "Capturada em",
    ])
    for opp in opportunities:
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
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=opportunities.csv",
        },
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
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Approve a proposal brief and advance the opportunity to in_progress.

    Atomic operation: updates both brief status and opportunity next_action.
    Only accepts briefs that are 'ready_for_review'.
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
    opportunity.next_action = "in_progress"

    db.commit()
    db.refresh(brief)

    return brief


@router.patch("/opportunities/{opportunity_id}/proposal-brief/reject")
def reject_proposal_brief(
    opportunity_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Reject a proposal brief, reverting it to draft.

    Only accepts briefs that are 'approved' or 'ready_for_review'.
    Does not change the opportunity next_action.
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
    from_date: str | None = Query(default=None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(default=None, description="Filter created_at <= date (YYYY-MM-DD)"),
    sort: str = Query(default="created_at", description="Sort by: created_at, id, status"),
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
    status: str | None = Query(default=None, description="Filter by brief status"),
    q: str | None = Query(default=None, description="Search keywords in title and offer reference"),
    from_date: str | None = Query(default=None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(default=None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Export proposal briefs for the authenticated tenant as CSV, respecting filters."""
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
        .order_by(ProposalBrief.id)
    )

    if status:
        query = query.where(ProposalBrief.status == status)

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

    rows = db.execute(query).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Oportunidade ID", "Título", "Referência", "Status", "Criada em",
    ])
    for row in rows:
        writer.writerow([
            row.id,
            row.opportunity_id,
            row.opportunity_title or "",
            row.offer_reference or "",
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
