"""add review queue items

Revision ID: b2713ddc906b
Revises: d7a4c6e91b20
Create Date: 2026-10-15 14:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2713ddc906b"
down_revision: Union[str, Sequence[str], None] = "d7a4c6e91b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "review_queue_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=100), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("intent", sa.String(length=60), nullable=True),
        sa.Column("draft_reply", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("operator_note", sa.Text(), nullable=True),
        sa.Column(
            "needs_human_review",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("flags_json", sa.JSON(), nullable=True),
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
            "event_id",
            name="uq_review_queue_items_company_event_id",
        ),
    )
    op.create_index(
        "ix_review_queue_items_company_id",
        "review_queue_items",
        ["company_id"],
    )
    op.create_index(
        "ix_review_queue_items_status",
        "review_queue_items",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_review_queue_items_status", table_name="review_queue_items")
    op.drop_index("ix_review_queue_items_company_id", table_name="review_queue_items")
    op.drop_table("review_queue_items")
