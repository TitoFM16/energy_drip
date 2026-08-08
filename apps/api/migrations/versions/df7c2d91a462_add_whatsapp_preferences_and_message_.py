"""add WhatsApp preferences and message category

Revision ID: df7c2d91a462
Revises: b19f9d8c36b4
Create Date: 2026-08-08 08:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "df7c2d91a462"
down_revision: str | None = "b19f9d8c36b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    notification_category = postgresql.ENUM(
        "TRANSACTIONAL", "MARKETING", name="notificationcategory"
    )
    notification_category.create(op.get_bind())

    op.add_column(
        "patients",
        sa.Column("whatsapp_opt_out", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "patients", sa.Column("whatsapp_opt_out_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "patients", sa.Column("whatsapp_opt_in_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("ALTER TYPE notificationstatus ADD VALUE IF NOT EXISTS 'SUPPRESSED'")
    op.add_column(
        "notification_messages",
        sa.Column(
            "category",
            notification_category,
            server_default="TRANSACTIONAL",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("notification_messages", "category")
    postgresql.ENUM(name="notificationcategory").drop(op.get_bind())

    # PostgreSQL cannot remove one enum label in place. Convert any rows
    # created with the new terminal state, then rebuild the original enum.
    op.execute("UPDATE notification_messages SET status = 'FAILED' WHERE status = 'SUPPRESSED'")
    op.execute("ALTER TYPE notificationstatus RENAME TO notificationstatus_with_suppressed")
    op.execute("CREATE TYPE notificationstatus AS ENUM ('PENDING', 'SENT', 'DELIVERED', 'FAILED')")
    op.execute(
        "ALTER TABLE notification_messages ALTER COLUMN status TYPE notificationstatus "
        "USING status::text::notificationstatus"
    )
    op.execute("DROP TYPE notificationstatus_with_suppressed")

    op.drop_column("patients", "whatsapp_opt_in_at")
    op.drop_column("patients", "whatsapp_opt_out_at")
    op.drop_column("patients", "whatsapp_opt_out")
