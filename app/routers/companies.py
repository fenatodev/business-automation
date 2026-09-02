from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import settings
from app.dependencies import (
    AuthenticatedContext,
    get_current_session,
    get_db,
    require_matching_company,
    require_roles,
)
from app.models import AccessAuditEvent, AuthSession, Company, CompanyMembership, User
from app.schemas import (
    CompanyAgentConfigResponse,
    CompanyAgentConfigUpdate,
    CompanyCreate,
    CompanyMembershipResponse,
    CompanyMembershipRoleUpdate,
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


def membership_response(
    membership: CompanyMembership,
    user: User,
) -> CompanyMembershipResponse:
    return CompanyMembershipResponse(
        id=membership.id,
        user_id=user.id,
        email=user.email_normalized,
        role=membership.role,
        is_active=membership.is_active,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


def locked_company_membership(
    db: Session,
    context: AuthenticatedContext,
    company_id: int,
    membership_id: int,
) -> CompanyMembership:
    require_matching_company(context, company_id)
    db.scalar(
        select(Company)
        .where(Company.id == context.company.id)
        .with_for_update()
    )
    membership = db.scalar(
        select(CompanyMembership).where(
            CompanyMembership.id == membership_id,
            CompanyMembership.company_id == context.company.id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )
    return membership


def commit_membership_change(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def ensure_not_last_active_owner(db: Session, membership: CompanyMembership) -> None:
    if not membership.is_active or membership.role != "owner":
        return

    active_owner_count = db.scalar(
        select(func.count())
        .select_from(CompanyMembership)
        .where(
            CompanyMembership.company_id == membership.company_id,
            CompanyMembership.role == "owner",
            CompanyMembership.is_active.is_(True),
        )
    )
    if active_owner_count == 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove the last active owner",
        )


@router.get(
    "/companies/{company_id}/memberships",
    response_model=list[CompanyMembershipResponse],
)
def list_company_memberships(
    company_id: int,
    context: Annotated[
        AuthenticatedContext,
        Depends(require_roles("owner")),
    ],
    db: Session = Depends(get_db),
):
    require_matching_company(context, company_id)
    memberships = db.execute(
        select(CompanyMembership, User)
        .join(User, User.id == CompanyMembership.user_id)
        .where(CompanyMembership.company_id == context.company.id)
        .order_by(CompanyMembership.id)
    ).all()
    return [membership_response(membership, user) for membership, user in memberships]


@router.patch(
    "/companies/{company_id}/memberships/{membership_id}/role",
    response_model=CompanyMembershipResponse,
)
def update_company_membership_role(
    company_id: int,
    membership_id: int,
    data: CompanyMembershipRoleUpdate,
    context: Annotated[
        AuthenticatedContext,
        Depends(require_roles("owner")),
    ],
    db: Session = Depends(get_db),
):
    membership = locked_company_membership(db, context, company_id, membership_id)
    if membership.role != data.role:
        ensure_not_last_active_owner(db, membership)
        old_role = membership.role
        membership.role = data.role
        db.add(
            AccessAuditEvent(
                company_id=context.company.id,
                actor_user_id=context.user.id,
                target_membership_id=membership.id,
                action="membership_role_changed",
                old_role=old_role,
                new_role=membership.role,
            )
        )
        commit_membership_change(db)
        db.refresh(membership)

    user = db.get(User, membership.user_id)
    return membership_response(membership, user)


def deactivate_membership(
    db: Session,
    context: AuthenticatedContext,
    company_id: int,
    membership_id: int,
) -> CompanyMembership:
    membership = locked_company_membership(db, context, company_id, membership_id)
    if not membership.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Membership is already inactive",
        )

    ensure_not_last_active_owner(db, membership)
    membership.is_active = False
    db.add(
        AccessAuditEvent(
            company_id=context.company.id,
            actor_user_id=context.user.id,
            target_membership_id=membership.id,
            action="membership_deactivated",
            old_is_active=True,
            new_is_active=False,
        )
    )
    commit_membership_change(db)
    db.refresh(membership)
    return membership


@router.post(
    "/companies/{company_id}/memberships/{membership_id}/deactivate",
    response_model=CompanyMembershipResponse,
)
def deactivate_company_membership(
    company_id: int,
    membership_id: int,
    context: Annotated[
        AuthenticatedContext,
        Depends(require_roles("owner")),
    ],
    db: Session = Depends(get_db),
):
    membership = deactivate_membership(db, context, company_id, membership_id)
    user = db.get(User, membership.user_id)
    return membership_response(membership, user)


@router.post(
    "/companies/{company_id}/memberships/{membership_id}/reactivate",
    response_model=CompanyMembershipResponse,
)
def reactivate_company_membership(
    company_id: int,
    membership_id: int,
    context: Annotated[
        AuthenticatedContext,
        Depends(require_roles("owner")),
    ],
    db: Session = Depends(get_db),
):
    membership = locked_company_membership(db, context, company_id, membership_id)
    if membership.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Membership is already active",
        )

    membership.is_active = True
    db.add(
        AccessAuditEvent(
            company_id=context.company.id,
            actor_user_id=context.user.id,
            target_membership_id=membership.id,
            action="membership_reactivated",
            old_is_active=False,
            new_is_active=True,
        )
    )
    commit_membership_change(db)
    db.refresh(membership)

    user = db.get(User, membership.user_id)
    return membership_response(membership, user)


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
