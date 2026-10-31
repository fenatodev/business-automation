from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, require_admin, require_operator
from app.models import Company
from app.schemas import CompanyAgentConfig, CompanyCreate


# WP-204 — In-memory agent config store (no migration required)
# Keyed by company_id; values are dicts with system_prompt and/or temperature
_agent_config_store: dict[int, dict[str, object]] = {}


router = APIRouter()


@router.post("/companies")
def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    _identity: AccessIdentity = Depends(require_admin),
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


@router.get("/companies")
def list_companies(
    db: Session = Depends(get_db),
    _identity: AccessIdentity = Depends(require_admin),
):
    return db.scalars(
        select(Company).order_by(Company.id)
    ).all()


@router.get("/companies/{company_id}/agent-config")
def get_agent_config(
    company_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Get the agent configuration for this company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    config = _agent_config_store.get(company_id, {})
    return CompanyAgentConfig(
        system_prompt=config.get("system_prompt"),
        temperature=config.get("temperature"),
    )


@router.put("/companies/{company_id}/agent-config")
def set_agent_config(
    company_id: int,
    data: CompanyAgentConfig,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Set the agent configuration for this company."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    config: dict[str, object] = {}
    if data.system_prompt is not None:
        config["system_prompt"] = data.system_prompt
    if data.temperature is not None:
        config["temperature"] = data.temperature
    _agent_config_store[company_id] = config

    return CompanyAgentConfig(
        system_prompt=config.get("system_prompt"),
        temperature=config.get("temperature"),
    )
