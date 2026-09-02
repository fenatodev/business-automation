from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import settings
from app.dependencies import get_current_session, get_db
from app.models import AuthSession, User
from app.schemas import AuthLoginRequest, AuthTokenResponse, CurrentUserResponse
from app.services.auth import (
    DUMMY_PASSWORD_HASH,
    create_session_token,
    hash_session_token,
    session_expiry,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthTokenResponse)
def login(data: AuthLoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email_normalized == data.email))
    password_hash = (
        user.password_hash if user is not None and user.is_active else DUMMY_PASSWORD_HASH
    )
    password_valid = verify_password(password_hash, data.password)
    if user is None or not user.is_active or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_session_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=session_expiry(settings.auth_session_ttl_hours),
        )
    )
    db.commit()

    return AuthTokenResponse(access_token=token)


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    authenticated: Annotated[tuple[User, AuthSession], Depends(get_current_session)],
):
    user, _ = authenticated
    return CurrentUserResponse(id=user.id, email=user.email_normalized)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    authenticated: Annotated[tuple[User, AuthSession], Depends(get_current_session)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _, session = authenticated
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
