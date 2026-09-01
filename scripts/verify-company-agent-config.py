#!/usr/bin/env python
import argparse
import os

from sqlalchemy import create_engine, text


EXPECTED_COLUMNS = {
    "agent_instructions": ("text", None),
    "agent_model": ("character varying", 120),
}


def verify(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        columns = connection.execute(
            text(
                "SELECT column_name, data_type, character_maximum_length, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'companies' "
                "AND column_name IN ('agent_instructions', 'agent_model')"
            )
        ).all()
        existing_companies_with_overrides = connection.execute(
            text(
                "SELECT count(*) FROM companies "
                "WHERE agent_instructions IS NOT NULL OR agent_model IS NOT NULL"
            )
        ).scalar_one()

    actual_columns = {
        row.column_name: (row.data_type, row.character_maximum_length, row.is_nullable)
        for row in columns
    }
    expected_columns = {
        name: (data_type, length, "YES")
        for name, (data_type, length) in EXPECTED_COLUMNS.items()
    }
    if actual_columns != expected_columns:
        raise SystemExit(
            f"Unexpected companies agent-config columns: {actual_columns!r}"
        )
    if existing_companies_with_overrides:
        raise SystemExit("Existing companies must retain null agent-config overrides")


def assert_absent(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        columns = connection.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'companies' "
                "AND column_name IN ('agent_instructions', 'agent_model')"
            )
        ).all()
    if columns:
        raise SystemExit("Company agent-config columns still exist after downgrade")


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
