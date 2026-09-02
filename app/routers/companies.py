from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import settings
from app.dependencies import (
    AuthenticatedContext,
    get_current_session,
    get_db,
    require_matching_company,
    require_roles,
)
from app.models import AuthSession, Company, CompanyMembership, User
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
    authenticated: Annotated[
        tuple[User, AuthSession],
        Depends(get_current_session),
    ],
    db: Session = Depends(get_db),
):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Company creation is not available via the public API",
    )


@router.get("/companies", response_model=list[CompanyResponse])
def list_companies(
    authenticated: Annotated[
        tuple[User, AuthSession],
        Depends(get_current_session),
    ],
    db: Session = Depends(get_db),
):
    user, _ = authenticated
    return db.scalars(
        select(Company)
        .join(CompanyMembership, CompanyMembership.company_id == Company.id)
        .where(
            CompanyMembership.user_id == user.id,
            CompanyMembership.is_active.is_(True),
        )
        .order_by(Company.id)
    ).all()


@router.get(
    "/companies/{company_id}/agent-config",
    response_model=CompanyAgentConfigResponse,
)
def get_company_agent_config(
    company_id: int,
    context: Annotated[
        AuthenticatedContext,
        Depends(require_roles("owner", "admin")),
    ],
    db: Session = Depends(get_db),
):
    require_matching_company(context, company_id)
    company = context.company

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
    context: Annotated[
        AuthenticatedContext,
        Depends(require_roles("owner", "admin")),
    ],
    db: Session = Depends(get_db),
):
    require_matching_company(context, company_id)
    company = context.company

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
