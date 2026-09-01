#!/usr/bin/env python
import argparse
import os

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


CONSTRAINT_NAME = "ck_conversations_exactly_one_owner"


def seed(database_url: str, channel: str) -> None:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        company_id = connection.execute(
            text(
                "INSERT INTO companies (name, slug) VALUES (:name, :slug) "
                "RETURNING id"
            ),
            {"name": f"Validation {channel}", "slug": f"validation-{channel}"},
        ).scalar_one()
        lead_id = connection.execute(
            text(
                "INSERT INTO leads (company_id, name, phone, source, status) "
                "VALUES (:company_id, 'Lead', '11999999999', 'validation', 'new') "
                "RETURNING id"
            ),
            {"company_id": company_id},
        ).scalar_one()
        customer_id = connection.execute(
            text(
                "INSERT INTO customers (company_id, name, phone) "
                "VALUES (:company_id, 'Customer', '11888888888') RETURNING id"
            ),
            {"company_id": company_id},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO conversations "
                "(company_id, lead_id, customer_id, channel, status) "
                "VALUES (:company_id, :lead_id, NULL, :channel, 'open'), "
                "(:company_id, NULL, :customer_id, :channel, 'open')"
            ),
            {
                "company_id": company_id,
                "lead_id": lead_id,
                "customer_id": customer_id,
                "channel": channel,
            },
        )


def seed_invalid(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        company_id = connection.execute(
            text(
                "INSERT INTO companies (name, slug) VALUES "
                "('Invalid validation', 'invalid-validation') RETURNING id"
            )
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO conversations "
                "(company_id, lead_id, customer_id, channel, status) "
                "VALUES (:company_id, NULL, NULL, 'invalid-existing', 'open')"
            ),
            {"company_id": company_id},
        )


def verify(database_url: str, channel: str) -> None:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        constraint = connection.execute(
            text(
                "SELECT convalidated FROM pg_constraint "
                "WHERE conname = :name AND contype = 'c'"
            ),
            {"name": CONSTRAINT_NAME},
        ).scalar_one_or_none()
        if constraint is not True:
            raise SystemExit("Conversation owner check constraint is missing or invalid")

        owner_ids = connection.execute(
            text(
                "SELECT company_id, lead_id, customer_id FROM conversations "
                "WHERE channel = :channel ORDER BY id LIMIT 2"
            ),
            {"channel": channel},
        ).all()

    if len(owner_ids) != 2:
        raise SystemExit("Expected two valid sentinel conversations")

    company_id = owner_ids[0].company_id
    lead_id = next(row.lead_id for row in owner_ids if row.lead_id is not None)
    customer_id = next(
        row.customer_id for row in owner_ids if row.customer_id is not None
    )
    invalid_owners = [
        {"lead_id": None, "customer_id": None},
        {"lead_id": lead_id, "customer_id": customer_id},
    ]
    for owner in invalid_owners:
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO conversations "
                        "(company_id, lead_id, customer_id, channel, status) "
                        "VALUES (:company_id, :lead_id, :customer_id, 'invalid', 'open')"
                    ),
                    {"company_id": company_id, **owner},
                )
        except IntegrityError:
            continue
        raise SystemExit("Invalid conversation owner combination was accepted")


def assert_absent(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        constraint = connection.execute(
            text("SELECT 1 FROM pg_constraint WHERE conname = :name"),
            {"name": CONSTRAINT_NAME},
        ).scalar_one_or_none()
    if constraint is not None:
        raise SystemExit("Conversation owner check constraint still exists")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("seed", "seed-invalid", "verify", "assert-absent"),
    )
    parser.add_argument("--channel", default="validation")
    args = parser.parse_args()
    database_url = os.environ["DATABASE_URL"]

    if args.action == "seed":
        seed(database_url, args.channel)
    elif args.action == "seed-invalid":
        seed_invalid(database_url)
    elif args.action == "verify":
        verify(database_url, args.channel)
    else:
        assert_absent(database_url)


if __name__ == "__main__":
    main()
