"""create borrowers, credit_history, audit_tasks

Revision ID: 9c304ac02b0a
Revises:
Create Date: 2026-09-10 11:29:25.188877

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9c304ac02b0a'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "borrowers",
        sa.Column("customer_id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("cpf", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("credit_score", sa.Integer(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "credit_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("borrowers.customer_id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_credit_history_customer_id", "credit_history", ["customer_id"])
    op.create_index("ix_credit_history_recorded_at", "credit_history", ["recorded_at"])

    op.create_table(
        "audit_tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_tasks_customer_id", "audit_tasks", ["customer_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_audit_tasks_customer_id", table_name="audit_tasks")
    op.drop_table("audit_tasks")

    op.drop_index("ix_credit_history_recorded_at", table_name="credit_history")
    op.drop_index("ix_credit_history_customer_id", table_name="credit_history")
    op.drop_table("credit_history")

    op.drop_table("borrowers")
