from typing import Generator as TypingGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import httpx

from app.auth import (
    AccessConfigurationError,
    AccessIdentity,
    authenticate_bearer_token,
)
from app.database import SessionLocal, settings
from app.services.intake_candidate_generator import (
    CandidateGenerator,
    OllamaCandidateGenerator,
    StaticCandidateGenerator,
    _is_loopback_url,
)


bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AccessIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        identity = authenticate_bearer_token(credentials.credentials)
    except AccessConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable",
        )

    if identity is None:
        raise _unauthorized()

    return identity


def require_admin(
    identity: AccessIdentity = Depends(get_current_identity),
) -> AccessIdentity:
    if identity.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return identity


def require_operator(
    identity: AccessIdentity = Depends(get_current_identity),
) -> AccessIdentity:
    if identity.role != "operator" or identity.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return identity


def ensure_company_match(
    identity: AccessIdentity,
    company_id: int,
) -> None:
    if identity.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


def require_operator_company(
    company_id: int,
    identity: AccessIdentity = Depends(require_operator),
) -> AccessIdentity:
    ensure_company_match(identity, company_id)
    return identity


def get_intake_generator() -> TypingGenerator[CandidateGenerator, None, None]:
    """Return the configured candidate generator for the intake endpoint.

    * ``static`` — always safe, no network.
    * ``ollama`` — requires loopback-only URL; returns 503 if misconfigured.

    The HTTP client (when used) is closed after the request scope.
    """
    client: httpx.Client | None = None
    try:
        mode = settings.intake_generator
        if mode == "static":
            yield StaticCandidateGenerator()
        elif mode == "ollama":
            if not _is_loopback_url(settings.ollama_url):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service unavailable",
                )
            client = httpx.Client(follow_redirects=False)
            generator = OllamaCandidateGenerator(
                client=client,
                model=settings.ollama_model,
                base_url=settings.ollama_url,
            )
            yield generator
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unavailable",
            )
    finally:
        if client is not None:
            client.close()
