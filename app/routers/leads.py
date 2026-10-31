import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
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
from app.schemas import LeadBulkStatus, LeadCreate, LeadUpdate


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


@router.post("/leads/import.csv")
def import_leads_csv(
    file: UploadFile,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Import leads from a CSV file.

    Expected columns: Nome, Telefone, Fonte, Interesse (optional).
    Duplicate phones are skipped. Max 500 rows per import.
    Returns: {imported, skipped, errors}
    """
    if file.content_type not in ("text/csv", "application/csv", None):
        raise HTTPException(
            status_code=400,
            detail="Apenas arquivos CSV são aceitos",
        )

    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    # Validate header
    if reader.fieldnames is None:
        raise HTTPException(
            status_code=400,
            detail="Arquivo CSV vazio ou inválido",
        )

    required_columns = {"Nome", "Telefone"}
    available = set(reader.fieldnames or [])
    if not required_columns.issubset(available):
        raise HTTPException(
            status_code=400,
            detail=f"Colunas obrigatórias ausentes: {required_columns - available}",
        )

    # Load existing phones for deduplication
    existing_phones = {
        row[0]
        for row in db.execute(
            select(Lead.phone).where(Lead.company_id == identity.company_id)
        ).fetchall()
    }

    imported = 0
    skipped = 0
    errors = 0
    max_rows = 500
    row_count = 0

    for row in reader:
        if row_count >= max_rows:
            break
        row_count += 1

        name = (row.get("Nome") or "").strip()
        phone = (row.get("Telefone") or "").strip()
        source = (row.get("Fonte") or "import").strip()
        interest = (row.get("Interesse") or "").strip() or None

        if not name or not phone:
            errors += 1
            continue

        if phone in existing_phones:
            skipped += 1
            continue

        new_lead = Lead(
            company_id=identity.company_id,
            name=name,
            phone=phone,
            source=source if source else "import",
            interest=interest,
            status="new",
        )
        db.add(new_lead)
        existing_phones.add(phone)
        imported += 1

    db.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "total_processed": row_count,
    }


@router.get("/leads")
def list_leads(
    status: str | None = None,
    q: str | None = Query(default=None, description="Search keywords in name and interest"),
    from_date: str | None = Query(default=None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(default=None, description="Filter created_at <= date (YYYY-MM-DD)"),
    sort: str = Query(default="id", description="Sort by: id, created_at, status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """List leads, optionally filtered by status, date range and searched by keywords."""
    query = select(Lead).where(Lead.company_id == identity.company_id)
    if status:
        query = query.where(Lead.status == status)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            func.lower(Lead.name).like(func.lower(pattern)) |
            func.lower(Lead.interest).like(func.lower(pattern))
        )
    # WP-152 — date range filter on created_at (ISO 8601 string comparison)
    if from_date:
        query = query.where(Lead.created_at >= from_date)
    if to_date:
        query = query.where(Lead.created_at <= to_date + "T23:59:59")
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
    from_date: str | None = Query(default=None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(default=None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Count leads, optionally filtered by status, date range and searched by keywords."""
    query = select(func.count()).select_from(Lead).where(Lead.company_id == identity.company_id)
    if status:
        query = query.where(Lead.status == status)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            func.lower(Lead.name).like(func.lower(pattern)) |
            func.lower(Lead.interest).like(func.lower(pattern))
        )
    # WP-152 — date range filter
    if from_date:
        query = query.where(Lead.created_at >= from_date)
    if to_date:
        query = query.where(Lead.created_at <= to_date + "T23:59:59")
    total = db.scalar(query)
    return {"total": total}


@router.get("/leads/export.csv")
def export_leads_csv(
    status: str | None = Query(None, description="Filter by status"),
    q: str | None = Query(None, description="Search keywords in name and interest"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Export tenant leads as a CSV file, respecting filters."""
    query = select(Lead).where(Lead.company_id == identity.company_id)
    if status:
        query = query.where(Lead.status == status)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            func.lower(Lead.name).like(func.lower(pattern)) |
            func.lower(Lead.interest).like(func.lower(pattern))
        )
    # WP-152 — date range filter
    if from_date:
        query = query.where(Lead.created_at >= from_date)
    if to_date:
        query = query.where(Lead.created_at <= to_date + "T23:59:59")
    leads = db.scalars(query.order_by(Lead.id)).all()

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


@router.post("/leads/bulk-status")
def bulk_update_lead_status(
    data: LeadBulkStatus,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Bulk update status for multiple leads (tenant-isolated)."""
    leads = db.scalars(
        select(Lead).where(
            Lead.id.in_(data.lead_ids),
            Lead.company_id == identity.company_id,
        )
    ).all()

    updated_ids = []
    for lead in leads:
        lead.status = data.status
        updated_ids.append(lead.id)

    db.commit()

    skipped = set(data.lead_ids) - set(updated_ids)

    return {
        "updated": len(updated_ids),
        "updated_ids": sorted(updated_ids),
        "skipped": sorted(skipped),
    }
