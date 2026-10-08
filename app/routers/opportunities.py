from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, require_operator
from app.models import Company, Opportunity, ProposalBrief
from app.schemas import (
    OpportunityCreate,
    OpportunityTriageUpdate,
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
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return db.scalars(
        select(Opportunity)
        .where(Opportunity.company_id == identity.company_id)
        .order_by(Opportunity.id)
    ).all()


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
