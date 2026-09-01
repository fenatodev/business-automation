from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import settings
from app.dependencies import get_db
from app.models import Company
from app.schemas import (
    CompanyAgentConfigResponse,
    CompanyAgentConfigUpdate,
    CompanyCreate,
    CompanyResponse,
)


router = APIRouter()


@router.post("/companies", response_model=CompanyResponse)
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


@router.get("/companies", response_model=list[CompanyResponse])
def list_companies(
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Company).order_by(Company.id)
    ).all()


@router.get(
    "/companies/{company_id}/agent-config",
    response_model=CompanyAgentConfigResponse,
)
def get_company_agent_config(
    company_id: int,
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return CompanyAgentConfigResponse(
        company_id=company.id,
        instructions=company.agent_instructions,
        model=company.agent_model,
        effective_model=company.agent_model or settings.ollama_model,
    )


@router.put(
    "/companies/{company_id}/agent-config",
    response_model=CompanyAgentConfigResponse,
)
def update_company_agent_config(
    company_id: int,
    data: CompanyAgentConfigUpdate,
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    company.agent_instructions = data.instructions
    company.agent_model = data.model
    db.commit()
    db.refresh(company)

    return CompanyAgentConfigResponse(
        company_id=company.id,
        instructions=company.agent_instructions,
        model=company.agent_model,
        effective_model=company.agent_model or settings.ollama_model,
    )
