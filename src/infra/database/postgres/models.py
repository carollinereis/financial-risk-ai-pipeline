import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Borrower(Base):
    """Registered borrower. Keyed by the same customer_id as the DuckDB `customers` table -
    Postgres is not a separate identity scheme, just a second store for what DuckDB is
    weak at (concurrent writes, task state, an append-only log).

    Bootstrapped from the existing customer roster (see seed.py) rather than a signup
    form - a real registration flow is a future step.
    """

    __tablename__ = "borrowers"

    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    cpf: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
    credit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CreditHistoryEntry(Base):
    """One time-series point for a borrower's credit score chart."""

    __tablename__ = "credit_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("borrowers.customer_id"), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class RiskScoreHistoryEntry(Base):
    """One time-series point of a borrower's XGBoost default-probability, logged per
    audit run. DuckDB's agent_evaluations table deliberately keeps only the current
    run (a re-audit deletes the previous one - see record_audit_results), so this is
    the only place a risk-score trend across runs actually exists.
    """

    __tablename__ = "risk_score_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("borrowers.customer_id"), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class AuditTask(Base):
    """Async job-state row for a committee audit run. PENDING -> PROCESSING -> COMPLETED|FAILED."""

    __tablename__ = "audit_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class DocumentExtractionTask(Base):
    """Async job-state row for a document-extraction run. Mirrors AuditTask's
    PENDING -> PROCESSING -> COMPLETED|FAILED shape but is its own table: this
    feature is independent of the committee pipeline and must not share state with it.
    """

    __tablename__ = "document_extraction_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    document_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class DocumentExtraction(Base):
    """One persisted, queryable extraction result per document run - typed columns
    rather than a JSON blob, so e.g. signature_present can be filtered on directly.

    review_status is "NEEDS_REVIEW" when the LLM's JSON output failed schema
    validation and some fields were dropped rather than guessed (see
    document_agent.py); "OK" when the full response parsed cleanly.
    """

    __tablename__ = "document_extractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("borrowers.customer_id"), nullable=False, index=True
    )
    document_name: Mapped[str] = mapped_column(String, nullable=False)
    borrower_name: Mapped[str | None] = mapped_column(String, nullable=True)
    loan_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    interest_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    term_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signature_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    review_status: Mapped[str] = mapped_column(String, nullable=False, default="OK")
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
