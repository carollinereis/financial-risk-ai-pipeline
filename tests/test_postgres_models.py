"""Unit tests for the Postgres ORM models (src/infra/database/postgres/models.py).

Runs against an in-memory SQLite engine rather than a real Postgres instance - the
SQLAlchemy-native equivalent of the DuckDB test-isolation rule: swap the engine, never
touch the real database.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infra.database.postgres.models import AuditTask, Base, Borrower, CreditHistoryEntry


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


class TestBorrower:
    def test_round_trips_by_customer_id(self, session):
        session.add(Borrower(customer_id=101, full_name="Ada Lovelace", credit_score=780))
        session.commit()

        fetched = session.get(Borrower, 101)
        assert fetched.full_name == "Ada Lovelace"
        assert fetched.credit_score == 780
        assert fetched.registered_at is not None

    def test_optional_pii_fields_default_to_none(self, session):
        session.add(Borrower(customer_id=102, full_name="Grace Hopper", credit_score=700))
        session.commit()

        fetched = session.get(Borrower, 102)
        assert fetched.email is None
        assert fetched.cpf is None
        assert fetched.phone_number is None


class TestCreditHistoryEntry:
    def test_orders_chronologically(self, session):
        session.add(Borrower(customer_id=201, full_name="Alan Turing", credit_score=650))
        session.add(CreditHistoryEntry(customer_id=201, score=600))
        session.add(CreditHistoryEntry(customer_id=201, score=650))
        session.commit()

        entries = (
            session.query(CreditHistoryEntry)
            .filter(CreditHistoryEntry.customer_id == 201)
            .order_by(CreditHistoryEntry.recorded_at)
            .all()
        )
        assert [e.score for e in entries] == [600, 650]


class TestAuditTask:
    def test_defaults_to_pending_with_generated_id(self, session):
        task = AuditTask(customer_id=301)
        session.add(task)
        session.commit()

        assert task.id  # uuid4 hex, non-empty
        assert task.status == "PENDING"
        assert task.result_json is None
        assert task.error is None

    def test_transitions_to_completed_with_result(self, session):
        task = AuditTask(customer_id=302)
        session.add(task)
        session.commit()

        task.status = "COMPLETED"
        task.result_json = '{"decision": "APPROVED"}'
        session.commit()

        fetched = session.get(AuditTask, task.id)
        assert fetched.status == "COMPLETED"
        assert fetched.result_json == '{"decision": "APPROVED"}'
