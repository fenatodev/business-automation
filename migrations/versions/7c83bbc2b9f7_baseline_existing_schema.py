"""baseline existing schema

Revision ID: 7c83bbc2b9f7
Revises: 0f4bc1c903c6
Create Date: 2026-08-31 20:10:57.794254

"""
from typing import Sequence, Union


revision: str = "7c83bbc2b9f7"
down_revision: Union[str, Sequence[str], None] = "0f4bc1c903c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Preserve the historical empty baseline."""
    pass


def downgrade() -> None:
    """Preserve the historical empty baseline."""
    pass
