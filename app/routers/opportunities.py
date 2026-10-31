import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, require_operator
from app.models import Company, Opportunity, ProposalBrief
from app.schemas import (
    OpportunityBulkTriage,
    OpportunityCreate,
    OpportunityTriageUpdate,
    OpportunityUpdate,
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


@router.get("/opportunities")
def list_opportunities(
    exclude_archived: bool = False,
    next_action: str | None = Query(None, description="Filter by next_action status"),
    q: str | None = Query(None, description="Search keywords in title and description"),
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
    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    brief = _get_proposal_brief(
        db,
        opportunity.id,
    )

    brief.offer_reference = data.offer_reference
    brief.diagnosis = data.diagnosis
    brief.scope = data.scope
    brief.deliverables = data.deliverables
    brief.acceptance_criteria = data.acceptance_criteria
    brief.assumptions = data.assumptions
    brief.risks = data.risks
    brief.status = data.status

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
