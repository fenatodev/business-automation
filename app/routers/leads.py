from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import (
    AuthenticatedContext,
    get_authenticated_context,
    get_db,
    require_matching_company,
)
from app.models import Lead
from app.schemas import LeadCreate, LeadUpdate


router = APIRouter()


@router.post("/leads")
def create_lead(
    lead: LeadCreate,
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    if lead.company_id != context.company.id:
        raise HTTPException(
            status_code=400,
            detail="company_id must match the authenticated company",
        )

    new_lead = Lead(
        company_id=context.company.id,
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
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Lead)
        .where(Lead.company_id == context.company.id)
        .order_by(Lead.id)
    ).all()


@router.get("/leads/{lead_id}")
def get_lead(
    lead_id: int,
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    lead = db.scalar(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.company_id == context.company.id,
        )
    )

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
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    lead = db.scalar(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.company_id == context.company.id,
        )
    )

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
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    require_matching_company(context, company_id)

    return db.scalars(
        select(Lead)
        .where(Lead.company_id == context.company.id)
        .order_by(Lead.id)
    ).all()
