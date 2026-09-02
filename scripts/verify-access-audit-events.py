#!/usr/bin/env python
import argparse
import os

from sqlalchemy import create_engine, text


TABLE = "access_audit_events"
CONSTRAINTS = {
    "ck_access_audit_events_action",
    "ck_access_audit_events_old_role",
    "ck_access_audit_events_new_role",
    "fk_access_audit_events_actor_user_id_users",
    "fk_access_audit_events_company_id_companies",
    "fk_access_audit_events_target_membership_id_company_memberships",
}


def verify(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        table_exists = connection.scalar(
            text(
                "SELECT EXISTS ("
                "SELECT FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :table)"
            ),
            {"table": TABLE},
        )
        if not table_exists:
            raise SystemExit(f"Missing table: {TABLE}")
        constraints = set(
            connection.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = to_regclass(:table)"
                ),
                {"table": TABLE},
            ).scalars()
        )
        if not CONSTRAINTS.issubset(constraints):
            raise SystemExit(f"Missing audit constraints: {CONSTRAINTS - constraints!r}")


def assert_absent(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        if connection.scalar(
            text(
                "SELECT EXISTS ("
                "SELECT FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :table)"
            ),
            {"table": TABLE},
        ):
            raise SystemExit(f"Table still exists after downgrade: {TABLE}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("verify", "assert-absent"))
    args = parser.parse_args()
    database_url = os.environ["DATABASE_URL"]
    if args.action == "verify":
        verify(database_url)
    else:
        assert_absent(database_url)


if __name__ == "__main__":
    main()
