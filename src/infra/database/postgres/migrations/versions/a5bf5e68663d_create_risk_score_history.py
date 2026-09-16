"""create risk_score_history

Revision ID: a5bf5e68663d
Revises: 9c304ac02b0a
Create Date: 2026-09-10 12:02:17.900217

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a5bf5e68663d"
down_revision: str | Sequence[str] | None = "9c304ac02b0a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "risk_score_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "customer_id", sa.Integer(), sa.ForeignKey("borrowers.customer_id"), nullable=False
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_score_history_customer_id", "risk_score_history", ["customer_id"])
    op.create_index("ix_risk_score_history_recorded_at", "risk_score_history", ["recorded_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_risk_score_history_recorded_at", table_name="risk_score_history")
    op.drop_index("ix_risk_score_history_customer_id", table_name="risk_score_history")
    op.drop_table("risk_score_history")
