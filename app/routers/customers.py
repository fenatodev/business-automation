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
from app.models import Customer, Lead
from app.schemas import CustomerCreate


router = APIRouter()


@router.get("/customers")
def list_customers(
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Customer)
        .where(Customer.company_id == context.company.id)
        .order_by(Customer.id)
    ).all()


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    customer = db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.company_id == context.company.id,
        )
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer


@router.get("/companies/{company_id}/customers")
def list_company_customers(
    company_id: int,
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    require_matching_company(context, company_id)

    return db.scalars(
        select(Customer)
        .where(Customer.company_id == context.company.id)
        .order_by(Customer.id)
    ).all()


@router.post("/customers")
def create_customer(
    customer: CustomerCreate,
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    if customer.company_id != context.company.id:
        raise HTTPException(
            status_code=400,
            detail="company_id must match the authenticated company",
        )

    new_customer = Customer(
        company_id=context.company.id,
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
    )

    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    return new_customer


@router.post("/leads/{lead_id}/convert")
def convert_lead_to_customer(
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

    existing_customer = db.scalar(
        select(Customer).where(
            Customer.lead_id == lead_id,
            Customer.company_id == context.company.id,
        )
    )

    if existing_customer:
        raise HTTPException(
            status_code=409,
            detail="Lead already converted to customer",
        )

    customer = Customer(
        company_id=lead.company_id,
        lead_id=lead.id,
        name=lead.name,
        phone=lead.phone,
    )

    lead.status = "won"

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer
