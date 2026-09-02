from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import settings
from app.models import AuthSession, Company, CompanyMembership, User
from app.services.auth import (
    bootstrap_initial_owner,
    hash_password,
    hash_session_token,
)


PASSWORD = "correct horse battery staple"


def create_user(db, email="owner@example.com", password=PASSWORD, is_active=True):
    user = User(
        email_normalized=email,
        password_hash=hash_password(password),
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    return user


def login(client, email="owner@example.com", password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_login_normalizes_email_and_persists_only_token_hash(client, db):
    user = create_user(db)

    response = login(client, email="  OWNER@EXAMPLE.COM  ")

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    token = response.json()["access_token"]
    assert token
    assert PASSWORD not in response.text

    auth_session = db.scalar(select(AuthSession).where(AuthSession.user_id == user.id))
    assert auth_session is not None
    assert auth_session.token_hash == hash_session_token(token)
    assert token not in auth_session.token_hash
    assert token not in str(auth_session.__dict__)


def test_login_rejects_invalid_credentials_and_inactive_users(client, db):
    create_user(db)
    create_user(db, email="inactive@example.com", is_active=False)

    for email, password in (
        ("missing@example.com", PASSWORD),
        ("owner@example.com", "wrong password"),
        ("inactive@example.com", PASSWORD),
    ):
        response = login(client, email=email, password=password)

        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid credentials"}
        assert response.headers["www-authenticate"] == "Bearer"


def test_auth_me_requires_a_valid_unexpired_session(client, db):
    user = create_user(db)
    token = login(client).json()["access_token"]

    valid_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert valid_response.status_code == 200
    assert valid_response.json() == {"id": user.id, "email": user.email_normalized}
    assert PASSWORD not in valid_response.text

    missing_response = client.get("/auth/me")
    unknown_response = client.get(
        "/auth/me", headers={"Authorization": "Bearer unknown-token"}
    )
    for response in (missing_response, unknown_response):
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"

    user.is_active = False
    db.commit()
    inactive_response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert inactive_response.status_code == 401
    assert inactive_response.headers["www-authenticate"] == "Bearer"

    user.is_active = True
    auth_session = db.scalar(select(AuthSession).where(AuthSession.user_id == user.id))
    auth_session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    expired_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert expired_response.status_code == 401
    assert expired_response.headers["www-authenticate"] == "Bearer"


def test_logout_revokes_the_session(client, db):
    user = create_user(db)
    token = login(client).json()["access_token"]

    response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 204
    assert response.content == b""
    auth_session = db.scalar(select(AuthSession).where(AuthSession.user_id == user.id))
    assert auth_session.revoked_at is not None

    rejected_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert rejected_response.status_code == 401
    assert rejected_response.headers["www-authenticate"] == "Bearer"


def test_login_uses_configured_session_ttl(client, db, monkeypatch):
    user = create_user(db)
    monkeypatch.setattr(settings, "auth_session_ttl_hours", 2)
    before_login = datetime.now(timezone.utc)

    response = login(client)

    assert response.status_code == 200
    auth_session = db.scalar(select(AuthSession).where(AuthSession.user_id == user.id))
    expires_at = auth_session.expires_at.replace(tzinfo=timezone.utc)
    assert expires_at >= before_login + timedelta(hours=2)
    assert expires_at <= datetime.now(timezone.utc) + timedelta(hours=2, seconds=2)


def test_login_rejects_invalid_request_lengths(client):
    response = client.post(
        "/auth/login",
        json={"email": "a" * 321, "password": PASSWORD},
    )
    assert response.status_code == 422

    response = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "a" * 1025},
    )
    assert response.status_code == 422


def test_bootstrap_initial_owner_requires_an_existing_company_and_no_users(db):
    with pytest.raises(ValueError, match="Company not found"):
        bootstrap_initial_owner(
            db,
            email="owner@example.com",
            password=PASSWORD,
            company_id=999,
        )

    company = Company(name="Acme", slug="acme")
    db.add(company)
    db.commit()

    user = bootstrap_initial_owner(
        db,
        email=" OWNER@EXAMPLE.COM ",
        password=PASSWORD,
        company_id=company.id,
    )
    db.commit()

    membership = db.scalar(
        select(CompanyMembership).where(CompanyMembership.user_id == user.id)
    )
    assert user.email_normalized == "owner@example.com"
    assert membership is not None
    assert membership.company_id == company.id
    assert membership.role == "owner"

    with pytest.raises(ValueError, match="initial user already exists"):
        bootstrap_initial_owner(
            db,
            email="another@example.com",
            password=PASSWORD,
            company_id=company.id,
        )


def test_company_membership_enforces_unique_user_company_and_known_roles(db):
    user = create_user(db)
    company = Company(name="Acme", slug="acme")
    db.add(company)
    db.commit()

    db.add(CompanyMembership(user_id=user.id, company_id=company.id, role="owner"))
    db.commit()

    db.add(CompanyMembership(user_id=user.id, company_id=company.id, role="member"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    db.add(CompanyMembership(user_id=user.id, company_id=company.id, role="invalid"))
    with pytest.raises(IntegrityError):
        db.flush()
