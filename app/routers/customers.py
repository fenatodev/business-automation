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
from app.models import Company, Customer, Lead
from app.schemas import CustomerCreate


router = APIRouter()


def _get_tenant_customer(
    db: Session,
    customer_id: int,
    company_id: int,
) -> Customer:
    customer = db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.company_id == company_id,
        )
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer


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


@router.get("/customers")
def list_customers(
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return db.scalars(
        select(Customer)
        .where(Customer.company_id == identity.company_id)
        .order_by(Customer.id)
    ).all()


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return _get_tenant_customer(
        db,
        customer_id,
        identity.company_id,
    )


@router.get("/companies/{company_id}/customers")
def list_company_customers(
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
        select(Customer)
        .where(Customer.company_id == company_id)
        .order_by(Customer.id)
    ).all()


@router.post("/customers")
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    ensure_company_match(identity, customer.company_id)

    company = db.scalar(
        select(Company).where(Company.id == identity.company_id)
    )

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    new_customer = Customer(
        company_id=identity.company_id,
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
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    lead = _get_tenant_lead(
        db,
        lead_id,
        identity.company_id,
    )

    existing_customer = db.scalar(
        select(Customer).where(
            Customer.lead_id == lead_id,
            Customer.company_id == identity.company_id,
        )
    )

    if existing_customer:
        raise HTTPException(
            status_code=409,
            detail="Lead already converted to customer",
        )

    customer = Customer(
        company_id=identity.company_id,
        lead_id=lead.id,
        name=lead.name,
        phone=lead.phone,
    )

    lead.status = "won"

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer
