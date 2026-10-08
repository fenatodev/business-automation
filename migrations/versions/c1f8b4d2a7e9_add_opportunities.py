"""add opportunities

Revision ID: c1f8b4d2a7e9
Revises: 963028cb1f76
Create Date: 2026-10-08 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1f8b4d2a7e9"
down_revision: Union[str, Sequence[str], None] = "963028cb1f76"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("external_url", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("budget", sa.String(length=120), nullable=True),
        sa.Column("deadline", sa.String(length=120), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "next_action",
            sa.String(length=30),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("triage_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "external_url",
            name="uq_opportunities_company_external_url",
        ),
    )
    op.create_index(
        op.f("ix_opportunities_company_id"),
        "opportunities",
        ["company_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_opportunities_company_id"),
        table_name="opportunities",
    )
    op.drop_table("opportunities")
