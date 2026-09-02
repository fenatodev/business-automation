#!/usr/bin/env python
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from app.dependencies import AuthenticatedContext
from app.models import AccessAuditEvent, Company, CompanyMembership, User
from app.routers.companies import deactivate_membership


def verify(database_url: str) -> None:
    engine = create_engine(database_url)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    suffix = uuid4().hex

    with session_factory() as db:
        company = Company(name=f"Concurrency {suffix}", slug=f"concurrency-{suffix}")
        first_user = User(
            email_normalized=f"first-{suffix}@example.com",
            password_hash="not-used-by-validation",
            is_active=True,
        )
        second_user = User(
            email_normalized=f"second-{suffix}@example.com",
            password_hash="not-used-by-validation",
            is_active=True,
        )
        db.add_all([company, first_user, second_user])
        db.flush()
        db.add_all(
            [
                CompanyMembership(
                    user_id=first_user.id,
                    company_id=company.id,
                    role="owner",
                    is_active=True,
                ),
                CompanyMembership(
                    user_id=second_user.id,
                    company_id=company.id,
                    role="owner",
                    is_active=True,
                ),
            ]
        )
        db.commit()
        company_id = company.id

    barrier = Barrier(2, timeout=5)

    def deactivate(user_id: int) -> str:
        with session_factory() as db:
            db.execute(text("SET LOCAL lock_timeout = '5s'"))
            company = db.get(Company, company_id)
            membership = db.scalar(
                select(CompanyMembership).where(
                    CompanyMembership.user_id == user_id,
                    CompanyMembership.company_id == company_id,
                )
            )
            user = db.get(User, user_id)
            context = AuthenticatedContext(
                user=user,
                session=None,  # type: ignore[arg-type]
                company=company,
                membership=membership,
            )
            barrier.wait()
            try:
                deactivate_membership(db, context, company_id, membership.id)
            except HTTPException as error:
                db.rollback()
                if error.status_code == 409:
                    return "conflict"
                raise
            return "success"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                deactivate,
                (first_user.id, second_user.id),
                timeout=15,
            )
        )

    if sorted(results) != ["conflict", "success"]:
        raise SystemExit(f"Expected one success and one conflict, got: {results!r}")

    with session_factory() as db:
        active_owners = db.scalar(
            select(func.count())
            .select_from(CompanyMembership)
            .where(
                CompanyMembership.company_id == company_id,
                CompanyMembership.role == "owner",
                CompanyMembership.is_active.is_(True),
            )
        )
        audit_events = db.scalar(
            select(func.count())
            .select_from(AccessAuditEvent)
            .where(AccessAuditEvent.company_id == company_id)
        )
    if active_owners != 1 or audit_events != 1:
        raise SystemExit(
            "Expected one active owner and one audit event after concurrent "
            f"deactivation, got owners={active_owners}, events={audit_events}"
        )


def main() -> None:
    verify(os.environ["DATABASE_URL"])


if __name__ == "__main__":
    main()
