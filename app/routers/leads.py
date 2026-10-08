from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import (
    ensure_company_match,
    get_db,
    require_operator,
    require_operator_company,
)
from app.models import Company, Lead
from app.schemas import LeadCreate, LeadUpdate


router = APIRouter()


def _get_tenant_lead(
    db: Session,
    lead_id: int,
    company_id: int,
) -> Lead:
    lead = db.scalar(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.company_id == company_id,
        )
    )

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    return lead


@router.post("/leads")
def create_lead(
    lead: LeadCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    ensure_company_match(identity, lead.company_id)

    company = db.scalar(
        select(Company).where(Company.id == identity.company_id)
    )

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    new_lead = Lead(
        company_id=identity.company_id,
        name=lead.name,
        phone=lead.phone,
        source=lead.source,
        interest=lead.interest,
        status="new",
    )

    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)

    return new_lead


@router.get("/leads")
def list_leads(
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return db.scalars(
        select(Lead)
        .where(Lead.company_id == identity.company_id)
        .order_by(Lead.id)
    ).all()


@router.get("/leads/{lead_id}")
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return _get_tenant_lead(
        db,
        lead_id,
        identity.company_id,
    )


@router.patch("/leads/{lead_id}")
def update_lead(
    lead_id: int,
    data: LeadUpdate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    lead = _get_tenant_lead(
        db,
        lead_id,
        identity.company_id,
    )

    lead.status = data.status

    db.commit()
    db.refresh(lead)

    return lead


@router.get("/companies/{company_id}/leads")
def list_company_leads(
    company_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator_company),
):
    company = db.scalar(
        select(Company).where(Company.id == identity.company_id)
    )

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return db.scalars(
        select(Lead)
        .where(Lead.company_id == company_id)
        .order_by(Lead.id)
    ).all()
