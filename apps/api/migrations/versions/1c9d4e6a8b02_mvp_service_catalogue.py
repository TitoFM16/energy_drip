"""Add the public service catalogue fields.

Revision ID: 1c9d4e6a8b02
Revises: 7a6c5e4d3b21
"""
from alembic import op
import sqlalchemy as sa

revision = "1c9d4e6a8b02"
down_revision = "7a6c5e4d3b21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("treatment_definitions", sa.Column("price", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("treatment_definitions", sa.Column("currency", sa.String(3), nullable=False, server_default="COP"))
    op.add_column("treatment_definitions", sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"))
    op.add_column("treatment_definitions", sa.Column("image_url", sa.String(2048), nullable=True))
    op.create_check_constraint("ck_service_price_nonnegative", "treatment_definitions", "price >= 0")
    op.create_check_constraint("ck_service_duration", "treatment_definitions", "duration_minutes BETWEEN 5 AND 480")
    op.create_check_constraint("ck_appointment_time_order", "appointments", "ends_at > starts_at")
    op.create_index("ix_appointments_practitioner_time", "appointments", ["practitioner_id", "starts_at", "ends_at"])


def downgrade() -> None:
    op.drop_index("ix_appointments_practitioner_time", table_name="appointments")
    op.drop_constraint("ck_appointment_time_order", "appointments", type_="check")
    op.drop_constraint("ck_service_duration", "treatment_definitions", type_="check")
    op.drop_constraint("ck_service_price_nonnegative", "treatment_definitions", type_="check")
    for name in ("image_url", "duration_minutes", "currency", "price"):
        op.drop_column("treatment_definitions", name)
