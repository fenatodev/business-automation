from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Company, Lead
from app.schemas import LeadCreate, LeadUpdate


router = APIRouter()


@router.post("/leads")
def create_lead(
    lead: LeadCreate,
    db: Session = Depends(get_db),
):
    company = db.get(Company, lead.company_id)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    new_lead = Lead(
        company_id=lead.company_id,
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
):
    return db.scalars(
        select(Lead).order_by(Lead.id)
    ).all()


@router.get("/leads/{lead_id}")
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
):
    lead = db.get(Lead, lead_id)

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    return lead


@router.patch("/leads/{lead_id}")
def update_lead(
    lead_id: int,
    data: LeadUpdate,
    db: Session = Depends(get_db),
):
    lead = db.get(Lead, lead_id)

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    lead.status = data.status

    db.commit()
    db.refresh(lead)

    return lead


@router.get("/companies/{company_id}/leads")
def list_company_leads(
    company_id: int,
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)

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
