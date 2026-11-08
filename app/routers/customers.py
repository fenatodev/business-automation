import csv
import io
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
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
from app.schemas import CustomerBulkDelete, CustomerCreate, CustomerUpdate


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
    sort: Literal["id", "created_at", "name"] = Query(default="id"),
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
    if sort == "name":
        stmt = stmt.order_by(Customer.name, Customer.id)
    elif sort == "created_at":
        stmt = stmt.order_by(Customer.created_at.desc(), Customer.id)
    else:
        stmt = stmt.order_by(Customer.id)
    customers = db.scalars(stmt).all()

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


@router.post("/customers/import.csv")
def import_customers_csv(
    file: UploadFile,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Import customers from a CSV file.

    Expected columns: Nome, Telefone, E-mail (optional).
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
            select(Customer.phone).where(Customer.company_id == identity.company_id)
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
        email = (row.get("E-mail") or "").strip() or None

        if not name or not phone:
            errors += 1
            continue

        if phone in existing_phones:
            skipped += 1
            continue

        new_customer = Customer(
            company_id=identity.company_id,
            name=name,
            phone=phone,
            email=email,
        )
        db.add(new_customer)
        existing_phones.add(phone)
        imported += 1

    db.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "total_processed": row_count,
    }


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
        return existing_customer

    customer = Customer(
        company_id=identity.company_id,
        lead_id=lead.id,
        name=lead.name,
        phone=lead.phone,
    )

    lead.status = "converted"

    db.add(customer)
    db.flush()

    # Link conversations: set customer_id on conversations that reference this lead
    from app.models import Conversation
    conversations = db.scalars(
        select(Conversation).where(
            Conversation.company_id == identity.company_id,
            Conversation.lead_id == lead.id,
        )
    ).all()
    for conv in conversations:
        conv.customer_id = customer.id

    db.commit()
    db.refresh(customer)

    return customer


@router.post("/customers/bulk-delete")
def bulk_delete_customers(
    data: CustomerBulkDelete,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Bulk delete multiple customers (tenant-isolated)."""
    customers = db.scalars(
        select(Customer).where(
            Customer.id.in_(data.customer_ids),
            Customer.company_id == identity.company_id,
        )
    ).all()

    deleted_ids = []
    for customer in customers:
        db.delete(customer)
        deleted_ids.append(customer.id)

    db.commit()

    skipped = set(data.customer_ids) - set(deleted_ids)

    return {
        "deleted": len(deleted_ids),
        "deleted_ids": sorted(deleted_ids),
        "skipped": sorted(skipped),
    }


@router.post("/customers/{customer_id}/suggest-opportunity")
def suggest_opportunity_from_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-272 — Suggest opportunity fields from customer context.

    Analyzes the customer data (name, email, phone, lead source) and suggests
    title, description, budget, deadline and requirements.
    Does NOT persist — returns only the suggestion.
    """
    customer = _get_tenant_customer(
        db,
        customer_id,
        identity.company_id,
    )

    # Build prompt from customer data
    prompt_parts = []
    prompt_parts.append(f"Nome: {customer.name}")
    if customer.phone:
        prompt_parts.append(f"Telefone: {customer.phone}")
    if customer.email:
        prompt_parts.append(f"E-mail: {customer.email}")
    if customer.lead_id:
        prompt_parts.append(f"Origem: Lead #{customer.lead_id}")
    prompt_parts.append("Tipo: Customer existente")
    customer_text = "\n".join(prompt_parts)

    system_prompt = (
        "Com base nos dados deste customer, sugira campos para criar uma oportunidade comercial.\n"
        "Retorne apenas JSON com esta estrutura:\n"
        '{"suggested_title": "título curto ou null", '
        '"suggested_description": "descrição ou null", '
        '"suggested_budget": "orçamento ou null", '
        '"suggested_deadline": "prazo ou null", '
        '"suggested_requirements": "requisitos ou null", '
        '"reasoning": "por que extraiu estes dados"}\n'
        "Se não encontrar um campo, use null."
    )

    try:
        from app.routers.companies import _agent_config_store, _record_agent_call
        from app.services.agent import AgentServiceError, generate_agent_reply

        company_config = _agent_config_store.get(identity.company_id, {})
        effective_temp = company_config.get("temperature")
        effective_max_tokens = company_config.get("max_tokens")
        effective_model = company_config.get("model")

        response = generate_agent_reply(
            message=customer_text,
            history=[],
            system_prompt=system_prompt,
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
            model=effective_model,
        )
        _record_agent_call(identity.company_id, success=True)
    except AgentServiceError:
        _record_agent_call(identity.company_id, success=False)
        raise HTTPException(
            status_code=503,
            detail="Agent service unavailable",
        )

    import json
    try:
        parsed = json.loads(response)
        return {
            "customer_id": customer.id,
            "suggested_title": parsed.get("suggested_title"),
            "suggested_description": parsed.get("suggested_description"),
            "suggested_budget": parsed.get("suggested_budget"),
            "suggested_deadline": parsed.get("suggested_deadline"),
            "suggested_requirements": parsed.get("suggested_requirements"),
            "reasoning": parsed.get("reasoning", response),
        }
    except (json.JSONDecodeError, AttributeError):
        return {
            "customer_id": customer.id,
            "suggested_title": None,
            "suggested_description": None,
            "suggested_budget": None,
            "suggested_deadline": None,
            "suggested_requirements": None,
            "reasoning": response,
        }


@router.post("/customers/{customer_id}/suggest-lead")
def suggest_lead_from_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-273 — Suggest lead fields from customer context.

    Analyzes the customer data and suggests name, phone and interest
    for creating a related lead. Does NOT persist — returns only the suggestion.
    """
    customer = _get_tenant_customer(
        db,
        customer_id,
        identity.company_id,
    )

    # Build prompt from customer data
    prompt_parts = []
    prompt_parts.append(f"Nome: {customer.name}")
    if customer.phone:
        prompt_parts.append(f"Telefone: {customer.phone}")
    if customer.email:
        prompt_parts.append(f"E-mail: {customer.email}")
    if customer.lead_id:
        prompt_parts.append(f"Origem: Lead #{customer.lead_id}")
    prompt_parts.append("Tipo: Customer existente")
    customer_text = "\n".join(prompt_parts)

    system_prompt = (
        "Com base nos dados deste customer, sugira campos para criar um lead relacionado.\n"
        "Retorne apenas JSON com esta estrutura:\n"
        '{"suggested_name": "nome ou null", '
        '"suggested_phone": "telefone ou null", '
        '"suggested_interest": "interesse ou null", '
        '"reasoning": "por que extraiu estes dados"}\n'
        "Se não encontrar um campo, use null."
    )

    try:
        from app.routers.companies import _agent_config_store, _record_agent_call
        from app.services.agent import AgentServiceError, generate_agent_reply

        company_config = _agent_config_store.get(identity.company_id, {})
        effective_temp = company_config.get("temperature")
        effective_max_tokens = company_config.get("max_tokens")
        effective_model = company_config.get("model")

        response = generate_agent_reply(
            message=customer_text,
            history=[],
            system_prompt=system_prompt,
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
            model=effective_model,
        )
        _record_agent_call(identity.company_id, success=True)
    except AgentServiceError:
        _record_agent_call(identity.company_id, success=False)
        raise HTTPException(
            status_code=503,
            detail="Agent service unavailable",
        )

    import json
    try:
        parsed = json.loads(response)
        return {
            "customer_id": customer.id,
            "suggested_name": parsed.get("suggested_name"),
            "suggested_phone": parsed.get("suggested_phone"),
            "suggested_interest": parsed.get("suggested_interest"),
            "reasoning": parsed.get("reasoning", response),
        }
    except (json.JSONDecodeError, AttributeError):
        return {
            "customer_id": customer.id,
            "suggested_name": None,
            "suggested_phone": None,
            "suggested_interest": None,
            "reasoning": response,
        }
