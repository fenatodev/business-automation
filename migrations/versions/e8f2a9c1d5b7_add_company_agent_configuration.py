"""add company agent configuration

Revision ID: e8f2a9c1d5b7
Revises: c14b8f9d2e3a
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8f2a9c1d5b7"
down_revision: Union[str, Sequence[str], None] = "c14b8f9d2e3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("agent_instructions", sa.Text(), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("agent_model", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("companies", "agent_model")
    op.drop_column("companies", "agent_instructions")
