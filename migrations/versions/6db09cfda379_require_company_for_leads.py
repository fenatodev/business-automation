"""require company for leads

Revision ID: 6db09cfda379
Revises: 4749a8ea474b
Create Date: 2026-08-31 21:11:45.377345

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6db09cfda379"
down_revision: Union[str, Sequence[str], None] = "4749a8ea474b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill legacy leads before requiring a company."""
    bind = op.get_bind()

    leads = sa.table(
        "leads",
        sa.column("company_id", sa.Integer()),
    )
    companies = sa.table(
        "companies",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String(length=120)),
        sa.column("slug", sa.String(length=80)),
    )

    null_lead_count = bind.scalar(
        sa.select(sa.func.count())
        .select_from(leads)
        .where(leads.c.company_id.is_(None))
    )

    if null_lead_count:
        company_ids = list(
            bind.scalars(
                sa.select(companies.c.id).order_by(companies.c.id)
            )
        )

        if not company_ids:
            legacy_company_id = bind.scalar(
                sa.insert(companies)
                .values(
                    name="Legacy Workspace",
                    slug="legacy-workspace",
                )
                .returning(companies.c.id)
            )
        elif len(company_ids) == 1:
            legacy_company_id = company_ids[0]
        else:
            raise RuntimeError(
                "Ambiguous company mapping: multiple companies exist while "
                "legacy leads have company_id IS NULL; manual mapping is required."
            )

        bind.execute(
            sa.update(leads)
            .where(leads.c.company_id.is_(None))
            .values(company_id=legacy_company_id)
        )

    op.alter_column(
        "leads",
        "company_id",
        existing_type=sa.INTEGER(),
        nullable=False,
    )


def downgrade() -> None:
    """Restore company_id nullability without rewriting migrated data."""
    op.alter_column(
        "leads",
        "company_id",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
