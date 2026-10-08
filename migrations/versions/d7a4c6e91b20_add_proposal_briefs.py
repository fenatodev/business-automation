"""add proposal briefs

Revision ID: d7a4c6e91b20
Revises: c1f8b4d2a7e9
Create Date: 2026-10-08 13:48:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7a4c6e91b20"
down_revision: Union[str, Sequence[str], None] = "c1f8b4d2a7e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "proposal_briefs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column(
            "offer_reference",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column("diagnosis", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("deliverables", sa.Text(), nullable=False),
        sa.Column(
            "acceptance_criteria",
            sa.Text(),
            nullable=False,
        ),
        sa.Column("assumptions", sa.Text(), nullable=True),
        sa.Column("risks", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="draft",
            nullable=False,
        ),
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
            ["opportunity_id"],
            ["opportunities.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "opportunity_id",
            name="uq_proposal_briefs_opportunity_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("proposal_briefs")
