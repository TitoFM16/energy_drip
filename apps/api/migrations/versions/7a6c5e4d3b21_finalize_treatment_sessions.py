"""finalize treatment sessions

Revision ID: 7a6c5e4d3b21
Revises: 4f2a8c7d9e10
Create Date: 2026-08-08 18:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a6c5e4d3b21"
down_revision: str | None = "4f2a8c7d9e10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "treatment_sessions",
        sa.Column("is_finalized", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "treatment_sessions",
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("treatment_sessions", "finalized_at")
    op.drop_column("treatment_sessions", "is_finalized")
