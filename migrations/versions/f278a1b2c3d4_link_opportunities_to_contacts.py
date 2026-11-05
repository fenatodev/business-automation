"""Link opportunities to an optional tenant contact.

Revision ID: f278a1b2c3d4
Revises: e063a1b2c3d4
"""
from alembic import op
import sqlalchemy as sa

revision = "f278a1b2c3d4"
down_revision = "e063a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("opportunities", sa.Column("lead_id", sa.Integer(), nullable=True))
    op.add_column("opportunities", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_opportunities_lead_id", "opportunities", "leads", ["lead_id"], ["id"])
    op.create_foreign_key("fk_opportunities_customer_id", "opportunities", "customers", ["customer_id"], ["id"])
    op.create_index("ix_opportunities_lead_id", "opportunities", ["lead_id"])
    op.create_index("ix_opportunities_customer_id", "opportunities", ["customer_id"])
    op.create_check_constraint(
        "ck_opportunities_one_contact", "opportunities",
        "NOT (lead_id IS NOT NULL AND customer_id IS NOT NULL)",
    )


def downgrade():
    op.drop_constraint("ck_opportunities_one_contact", "opportunities", type_="check")
    op.drop_index("ix_opportunities_customer_id", table_name="opportunities")
    op.drop_index("ix_opportunities_lead_id", table_name="opportunities")
    op.drop_constraint("fk_opportunities_customer_id", "opportunities", type_="foreignkey")
    op.drop_constraint("fk_opportunities_lead_id", "opportunities", type_="foreignkey")
    op.drop_column("opportunities", "customer_id")
    op.drop_column("opportunities", "lead_id")
