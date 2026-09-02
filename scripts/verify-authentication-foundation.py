#!/usr/bin/env python
import argparse
import os

from sqlalchemy import create_engine, text


AUTH_TABLES = {"users", "company_memberships", "auth_sessions"}


def existing_auth_tables(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        return set(
            connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' "
                    "AND table_name IN ('users', 'company_memberships', 'auth_sessions')"
                )
            ).scalars()
        )


def verify(database_url: str) -> None:
    tables = existing_auth_tables(database_url)
    if tables != AUTH_TABLES:
        raise SystemExit(f"Unexpected authentication tables: {tables!r}")


def assert_absent(database_url: str) -> None:
    tables = existing_auth_tables(database_url)
    if tables:
        raise SystemExit(f"Authentication tables still exist after downgrade: {tables!r}")


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
