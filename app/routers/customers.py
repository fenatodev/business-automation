from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Company, Customer, Lead
from app.schemas import CustomerCreate


router = APIRouter()


@router.get("/customers")
def list_customers(
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Customer).order_by(Customer.id)
    ).all()


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
):
    customer = db.get(Customer, customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer


@router.get("/companies/{company_id}/customers")
def list_company_customers(
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
        select(Customer)
        .where(Customer.company_id == company_id)
        .order_by(Customer.id)
    ).all()


@router.post("/customers")
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
):
    company = db.get(Company, customer.company_id)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    new_customer = Customer(
        company_id=customer.company_id,
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
):
    lead = db.get(Lead, lead_id)

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    existing_customer = db.scalar(
        select(Customer).where(Customer.lead_id == lead_id)
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
