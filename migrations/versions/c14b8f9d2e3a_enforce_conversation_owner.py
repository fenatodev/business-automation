"""enforce conversation owner

Revision ID: c14b8f9d2e3a
Revises: 963028cb1f76
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c14b8f9d2e3a"
down_revision: Union[str, Sequence[str], None] = "963028cb1f76"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = "ck_conversations_exactly_one_owner"
CONSTRAINT_EXPRESSION = (
    "(lead_id IS NOT NULL AND customer_id IS NULL) OR "
    "(lead_id IS NULL AND customer_id IS NOT NULL)"
)


def upgrade() -> None:
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "conversations",
        CONSTRAINT_EXPRESSION,
    )


def downgrade() -> None:
    op.drop_constraint(
        CONSTRAINT_NAME,
        "conversations",
        type_="check",
    )
