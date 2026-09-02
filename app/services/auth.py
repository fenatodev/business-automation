from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, CompanyMembership, User


password_hasher = PasswordHasher()
DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$P57CEvNl1zSBj72JeYTPdg$"
    "yb3yee3v3yulY+FMzUnKpFgRv8H7KR2XX/lpg2KDksg"
)


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def bootstrap_initial_owner(
    db: Session,
    *,
    email: str,
    password: str,
    company_id: int,
) -> User:
    if db.scalar(select(User.id).limit(1)) is not None:
        raise ValueError("An initial user already exists")

    company = db.get(Company, company_id)
    if company is None:
        raise ValueError("Company not found")

    user = User(
        email_normalized=normalize_email(email),
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(CompanyMembership(user_id=user.id, company_id=company.id, role="owner"))
    return user


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False


def create_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def session_expiry(ttl_hours: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
