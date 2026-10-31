import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import (
    ensure_company_match,
    get_db,
    require_operator,
    require_operator_company,
)
from app.models import Company, Customer, Lead
from app.schemas import CustomerCreate, CustomerUpdate


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
    q: str | None = Query(None, description="Search keywords in name, phone, and email"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    sort: str = Query(default="id", description="Sort by: id, created_at, name"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """List customers with optional search, date filter, sort, and pagination."""
    stmt = (
        select(Customer)
        .where(Customer.company_id == identity.company_id)
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            Customer.name.like(pattern)
            | Customer.phone.like(pattern)
            | Customer.email.like(pattern)
        )
    # WP-153 — date range filter
    if from_date:
        stmt = stmt.where(Customer.created_at >= from_date)
    if to_date:
        stmt = stmt.where(Customer.created_at <= to_date + "T23:59:59")

    if sort == "name":
        stmt = stmt.order_by(Customer.name)
    elif sort == "created_at":
        stmt = stmt.order_by(Customer.created_at.desc())
    else:
        stmt = stmt.order_by(Customer.id)

    stmt = stmt.offset(offset).limit(limit)
    return db.scalars(stmt).all()


@router.get("/customers/count")
def count_customers(
    q: str | None = Query(None, description="Search keywords in name, phone, and email"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Count customers with optional search and date filter."""
    stmt = (
        select(func.count())
        .select_from(Customer)
        .where(Customer.company_id == identity.company_id)
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            Customer.name.like(pattern)
            | Customer.phone.like(pattern)
            | Customer.email.like(pattern)
        )
    # WP-153 — date range filter
    if from_date:
        stmt = stmt.where(Customer.created_at >= from_date)
    if to_date:
        stmt = stmt.where(Customer.created_at <= to_date + "T23:59:59")

    total = db.scalar(stmt)
    return {"total": total}


@router.get("/customers/export.csv")
def export_customers_csv(
    q: str | None = Query(None, description="Search keywords in name, phone, and email"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Export tenant customers as a CSV file, respecting filters."""
    stmt = select(Customer).where(Customer.company_id == identity.company_id)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            Customer.name.like(pattern)
            | Customer.phone.like(pattern)
            | Customer.email.like(pattern)
        )
    # WP-153 — date range filter
    if from_date:
        stmt = stmt.where(Customer.created_at >= from_date)
    if to_date:
        stmt = stmt.where(Customer.created_at <= to_date + "T23:59:59")
    customers = db.scalars(stmt.order_by(Customer.id)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Nome", "Telefone", "E-mail", "Lead origem",
        "Criado em",
    ])
    for customer in customers:
        writer.writerow([
            customer.id,
            customer.name,
            customer.phone or "",
            customer.email or "",
            customer.lead_id or "",
            customer.created_at.isoformat() if customer.created_at else "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=customers.csv",
        },
    )


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


@router.patch("/customers/{customer_id}")
def update_customer(
    customer_id: int,
    update: CustomerUpdate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Update customer name, phone, and/or email. Tenant-isolated."""
    customer = _get_tenant_customer(
        db,
        customer_id,
        identity.company_id,
    )

    data = update.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=400,
            detail="No fields to update",
        )

    if "name" in data:
        customer.name = data["name"]
    if "phone" in data:
        customer.phone = data["phone"]
    if "email" in data:
        customer.email = data["email"]

    db.commit()
    db.refresh(customer)
    return customer


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
