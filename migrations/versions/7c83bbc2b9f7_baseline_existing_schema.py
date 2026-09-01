"""baseline existing schema

Revision ID: 7c83bbc2b9f7
Revises: 
Create Date: 2026-08-31 20:10:57.794254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c83bbc2b9f7'
down_revision: Union[str, Sequence[str], None] = '0f4bc1c903c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
