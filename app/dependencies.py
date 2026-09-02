from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import AuthSession, User
from app.services.auth import hash_session_token


bearer_scheme = HTTPBearer(auto_error=False)


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
