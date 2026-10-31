from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.patch("/opportunities/{opportunity_id}")
def update_opportunity(
    opportunity_id: int,
    data: OpportunityUpdate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Update opportunity title and/or description (tenant-isolated)."""
    opportunity = _get_tenant_opportunity(
        db,
        opportunity_id,
        identity.company_id,
    )

    if data.title is not None:
        opportunity.title = data.title
    if data.description is not None:
        opportunity.description = data.description

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
    Opportunities that don't exist or belong to another tenant are skipped.
    The response includes counts of updated and skipped opportunities.
    """
    opportunities = db.scalars(
        select(Opportunity).where(
            Opportunity.id.in_(data.opportunity_ids),
            Opportunity.company_id == identity.company_id,
        )
    ).all()

    updated_ids = []
    skipped_count = len(data.opportunity_ids) - len(opportunities)

    for opportunity in opportunities:
        opportunity.next_action = data.next_action
        opportunity.triage_note = data.triage_note
        updated_ids.append(opportunity.id)

    db.commit()

    return {
        "updated": len(updated_ids),
        "updated_ids": updated_ids,
        "skipped": skipped_count,
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
