"""create document_extraction_tasks, document_extractions

Revision ID: aa70d910c9b6
Revises: a5bf5e68663d
Create Date: 2026-09-23 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa70d910c9b6"
down_revision: str | Sequence[str] | None = "a5bf5e68663d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "document_extraction_tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("document_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_document_extraction_tasks_customer_id", "document_extraction_tasks", ["customer_id"]
    )

    op.create_table(
        "document_extractions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "customer_id", sa.Integer(), sa.ForeignKey("borrowers.customer_id"), nullable=False
        ),
        sa.Column("document_name", sa.String(), nullable=False),
        sa.Column("borrower_name", sa.String(), nullable=True),
        sa.Column("loan_amount", sa.Float(), nullable=True),
        sa.Column("interest_rate", sa.Float(), nullable=True),
        sa.Column("term_months", sa.Integer(), nullable=True),
        sa.Column("signature_present", sa.Boolean(), nullable=False),
        sa.Column("risk_flags_json", sa.Text(), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_extractions_customer_id", "document_extractions", ["customer_id"])
    op.create_index(
        "ix_document_extractions_extracted_at", "document_extractions", ["extracted_at"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_document_extractions_extracted_at", table_name="document_extractions")
    op.drop_index("ix_document_extractions_customer_id", table_name="document_extractions")
    op.drop_table("document_extractions")

    op.drop_index(
        "ix_document_extraction_tasks_customer_id", table_name="document_extraction_tasks"
    )
    op.drop_table("document_extraction_tasks")
