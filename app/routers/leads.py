import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select, desc
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
    status: str | None = None,
    q: str | None = Query(default=None, description="Search keywords in name and interest"),
    sort: str = Query(default="id", description="Sort by: id, created_at, status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """List leads, optionally filtered by status and searched by keywords."""
    query = select(Lead).where(Lead.company_id == identity.company_id)
    if status:
        query = query.where(Lead.status == status)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            func.lower(Lead.name).like(func.lower(pattern)) |
            func.lower(Lead.interest).like(func.lower(pattern))
        )
    if sort == "created_at":
        query = query.order_by(desc(Lead.created_at), Lead.id)
    elif sort == "status":
        query = query.order_by(Lead.status, Lead.id)
    else:
        query = query.order_by(Lead.id)
    query = query.offset(offset).limit(limit)
    return db.scalars(query).all()


@router.get("/leads/count")
def count_leads(
    status: str | None = None,
    q: str | None = Query(default=None, description="Search keywords in name and interest"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Count leads, optionally filtered by status and searched by keywords."""
    query = select(func.count()).select_from(Lead).where(Lead.company_id == identity.company_id)
    if status:
        query = query.where(Lead.status == status)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            func.lower(Lead.name).like(func.lower(pattern)) |
            func.lower(Lead.interest).like(func.lower(pattern))
        )
    total = db.scalar(query)
    return {"total": total}


@router.get("/leads/export.csv")
def export_leads_csv(
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Export all tenant leads as a CSV file."""
    leads = db.scalars(
        select(Lead)
        .where(Lead.company_id == identity.company_id)
        .order_by(Lead.id)
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Nome", "Telefone", "E-mail", "Fonte", "Interesse",
        "Status", "Criado em",
    ])
    for lead in leads:
        writer.writerow([
            lead.id,
            lead.name,
            lead.phone or "",
            lead.source or "",
            lead.interest or "",
            lead.status or "",
            lead.created_at.isoformat() if lead.created_at else "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=leads.csv",
        },
    )


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

    if data.status is not None:
        lead.status = data.status
    if data.interest is not None:
        lead.interest = data.interest

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
