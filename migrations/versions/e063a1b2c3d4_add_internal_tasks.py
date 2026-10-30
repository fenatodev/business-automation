"""Add durable internal synthetic tasks.

Revision ID: e063a1b2c3d4
Revises: b2713ddc906b
"""
from alembic import op
import sqlalchemy as sa

revision = "e063a1b2c3d4"
down_revision = "b2713ddc906b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "internal_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("event_id", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_token", sa.String(36), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "event_id", name="uq_internal_tasks_company_event"),
        sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name="ck_internal_tasks_status"),
        sa.CheckConstraint("attempts >= 0 AND attempts <= 3", name="ck_internal_tasks_attempts"),
    )
    op.create_index("ix_internal_tasks_ready", "internal_tasks", ["status", "available_at"])
    op.create_index("ix_internal_tasks_lease", "internal_tasks", ["status", "lease_until"])


def downgrade():
    op.drop_index("ix_internal_tasks_lease", table_name="internal_tasks")
    op.drop_index("ix_internal_tasks_ready", table_name="internal_tasks")
    op.drop_table("internal_tasks")
