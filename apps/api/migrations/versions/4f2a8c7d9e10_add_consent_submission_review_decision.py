"""add consent submission review decision

Revision ID: 4f2a8c7d9e10
Revises: df7c2d91a462
Create Date: 2026-08-08 17:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4f2a8c7d9e10"
down_revision: str | None = "df7c2d91a462"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    review_decision = postgresql.ENUM("APPROVED", "REJECTED", name="consentreviewdecision")
    review_decision.create(op.get_bind())
    op.add_column(
        "consent_submissions",
        sa.Column("review_decision", review_decision, nullable=True),
    )
    op.add_column(
        "consent_submissions",
        sa.Column("review_rationale", sa.String(length=2000), nullable=True),
    )
    op.add_column(
        "consent_submissions",
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "consent_submissions",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_consent_submissions_review_metadata_complete",
        "consent_submissions",
        "(review_decision IS NULL AND review_rationale IS NULL "
        "AND reviewed_by_user_id IS NULL AND reviewed_at IS NULL) OR "
        "(review_decision IS NOT NULL AND review_rationale IS NOT NULL "
        "AND reviewed_by_user_id IS NOT NULL AND reviewed_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_consent_submissions_review_metadata_complete",
        "consent_submissions",
        type_="check",
    )
    op.drop_column("consent_submissions", "reviewed_at")
    op.drop_column("consent_submissions", "reviewed_by_user_id")
    op.drop_column("consent_submissions", "review_rationale")
    op.drop_column("consent_submissions", "review_decision")
    postgresql.ENUM(name="consentreviewdecision").drop(op.get_bind())
