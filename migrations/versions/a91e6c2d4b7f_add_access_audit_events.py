"""add access audit events

Revision ID: a91e6c2d4b7f
Revises: f2c7a6b8d9e0
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a91e6c2d4b7f"
down_revision: Union[str, Sequence[str], None] = "f2c7a6b8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "access_audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("target_membership_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("old_role", sa.String(length=20), nullable=True),
        sa.Column("new_role", sa.String(length=20), nullable=True),
        sa.Column("old_is_active", sa.Boolean(), nullable=True),
        sa.Column("new_is_active", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('membership_role_changed', 'membership_deactivated', "
            "'membership_reactivated')",
            name="ck_access_audit_events_action",
        ),
        sa.CheckConstraint(
            "old_role IS NULL OR old_role IN ('owner', 'admin', 'member')",
            name="ck_access_audit_events_old_role",
        ),
        sa.CheckConstraint(
            "new_role IS NULL OR new_role IN ('owner', 'admin', 'member')",
            name="ck_access_audit_events_new_role",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_access_audit_events_actor_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_access_audit_events_company_id_companies",
        ),
        sa.ForeignKeyConstraint(
            ["target_membership_id"],
            ["company_memberships.id"],
            name="fk_access_audit_events_target_membership_id_company_memberships",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_access_audit_events"),
    )
    op.create_index(
        "ix_access_audit_events_actor_user_id",
        "access_audit_events",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_access_audit_events_company_id",
        "access_audit_events",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_access_audit_events_target_membership_id",
        "access_audit_events",
        ["target_membership_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_access_audit_events_target_membership_id",
        table_name="access_audit_events",
    )
    op.drop_index(
        "ix_access_audit_events_company_id",
        table_name="access_audit_events",
    )
    op.drop_index(
        "ix_access_audit_events_actor_user_id",
        table_name="access_audit_events",
    )
    op.drop_table("access_audit_events")
