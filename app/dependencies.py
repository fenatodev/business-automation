from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import AuthSession, Company, CompanyMembership, User
from app.services.auth import hash_session_token


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedContext:
    user: User
    session: AuthSession
    company: Company
    membership: CompanyMembership


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_current_session(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> tuple[User, AuthSession]:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == hash_session_token(credentials.credentials),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(timezone.utc),
        )
    )
    if session is None:
        raise unauthorized

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise unauthorized

    return user, session


def get_authenticated_context(
    authenticated: Annotated[tuple[User, AuthSession], Depends(get_current_session)],
    db: Annotated[Session, Depends(get_db)],
    tenant_company_id: Annotated[
        int | None,
        Header(alias="X-Company-ID"),
    ] = None,
) -> AuthenticatedContext:
    if tenant_company_id is None or tenant_company_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Company-ID header is required",
        )

    user, auth_session = authenticated
    membership = db.scalar(
        select(CompanyMembership).where(
            CompanyMembership.user_id == user.id,
            CompanyMembership.company_id == tenant_company_id,
            CompanyMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    company = db.get(Company, tenant_company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    return AuthenticatedContext(
        user=user,
        session=auth_session,
        company=company,
        membership=membership,
    )


def require_roles(*allowed_roles: str):
    def dependency(
        context: Annotated[
            AuthenticatedContext,
            Depends(get_authenticated_context),
        ],
    ) -> AuthenticatedContext:
        if context.membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return context

    return dependency


def require_matching_company(
    context: AuthenticatedContext,
    company_id: int,
) -> None:
    if company_id != context.company.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
