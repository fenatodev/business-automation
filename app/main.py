from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Company, Customer, Lead


app = FastAPI(
    title="Fenato Business Automation API",
    version="0.1.0",
)


# =========================================================
# SCHEMAS
# =========================================================

class LeadCreate(BaseModel):
    company_id: int
    name: str
    phone: str
    source: str
    interest: str | None = None


class CustomerCreate(BaseModel):
    company_id: int
    name: str
    phone: str
    email: str | None = None    


class LeadUpdate(BaseModel):
    status: Literal[
        "new",
        "contacted",
        "qualified",
        "proposal",
        "won",
        "lost",
    ]


class CompanyCreate(BaseModel):
    name: str
    slug: str


# =========================================================
# DATABASE
# =========================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================================================
# HEALTH
# =========================================================

@app.get("/")
def root():
    return {
        "name": "Fenato Business Automation API",
        "status": "running",
    }

@app.post("/companies")
def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(Company).where(Company.slug == company.slug)
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Company slug already exists",
        )

    new_company = Company(
        name=company.name,
        slug=company.slug,
    )

    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    return new_company


@app.get("/companies")
def list_companies(
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Company).order_by(Company.id)
    ).all()


@app.get("/customers")
def list_customers(
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Customer).order_by(Customer.id)
    ).all()


@app.post("/customers")
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


@app.post("/leads/{lead_id}/convert")
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


# =========================================================
# LEADS
# =========================================================

@app.post("/leads")
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


@app.get("/leads")
def list_leads(
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Lead).order_by(Lead.id)
    ).all()


@app.get("/leads/{lead_id}")
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


@app.patch("/leads/{lead_id}")
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


# =========================================================
# COMPANY LEADS
# =========================================================

@app.get("/companies/{company_id}/leads")
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