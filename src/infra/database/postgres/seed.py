"""One-off bootstrap: mirrors the existing customer roster into Postgres as registered
Borrowers, and backfills synthetic CreditHistoryEntry / RiskScoreHistoryEntry trends per
borrower so both history charts aren't empty before any audit has run.

Run from the repo root: python -m src.infra.database.postgres.seed
"""

import random
from datetime import UTC, datetime, timedelta

from src.infra.database.database import get_read_connection
from src.infra.database.postgres.models import (
    Base,
    Borrower,
    CreditHistoryEntry,
    RiskScoreHistoryEntry,
)
from src.infra.database.postgres.session import engine, get_session

BACKFILL_POINTS = 6
BACKFILL_INTERVAL_DAYS = 30
CREDIT_SCORE_NOISE = 20  # +/- points of plausible drift on backfilled credit-score history
RISK_SCORE_NOISE = 0.05  # +/- probability of plausible drift on backfilled risk-score history


def _fetch_customers() -> list[dict]:
    with get_read_connection() as conn:
        df = conn.execute(
            "SELECT customer_id, full_name, email, cpf, phone_number, credit_score, risk_score "
            "FROM customers ORDER BY customer_id"
        ).df()
    return df.to_dict(orient="records")


def _backfill_series(current_value: float, noise: float, low: float, high: float) -> list[float]:
    """Builds BACKFILL_POINTS values oldest-first, randomly walking from `current_value`
    backwards so the walk's own endpoint (index 0, i.e. today) lands exactly on it -
    the same trend shape for either score.
    """
    values = [None] * BACKFILL_POINTS
    values[0] = current_value
    value = current_value
    for i in range(1, BACKFILL_POINTS):
        value = max(low, min(high, value + random.uniform(-noise, noise)))
        values[i] = value
    return list(reversed(values))


def _backfill_credit_history(customer_id: int, current_score: int) -> list[CreditHistoryEntry]:
    now = datetime.now(UTC)
    scores = _backfill_series(current_score, CREDIT_SCORE_NOISE, 300, 850)
    return [
        CreditHistoryEntry(
            customer_id=customer_id,
            score=round(score),
            recorded_at=now - timedelta(days=i * BACKFILL_INTERVAL_DAYS),
        )
        for i, score in zip(range(BACKFILL_POINTS - 1, -1, -1), scores, strict=True)
    ]


def _backfill_risk_history(customer_id: int, current_score: float) -> list[RiskScoreHistoryEntry]:
    now = datetime.now(UTC)
    scores = _backfill_series(current_score, RISK_SCORE_NOISE, 0.0, 1.0)
    return [
        RiskScoreHistoryEntry(
            customer_id=customer_id,
            score=score,
            recorded_at=now - timedelta(days=i * BACKFILL_INTERVAL_DAYS),
        )
        for i, score in zip(range(BACKFILL_POINTS - 1, -1, -1), scores, strict=True)
    ]


def run() -> None:
    """Idempotent: registering a borrower and backfilling each history table are
    checked independently, so re-running after adding a new history table (as
    happened with risk_score_history) still backfills it for borrowers that were
    already registered.
    """
    Base.metadata.create_all(engine)

    customers = _fetch_customers()
    with get_session() as session:
        for row in customers:
            customer_id = int(row["customer_id"])

            if session.get(Borrower, customer_id) is None:
                session.add(
                    Borrower(
                        customer_id=customer_id,
                        full_name=row["full_name"],
                        email=row.get("email"),
                        cpf=row.get("cpf"),
                        phone_number=row.get("phone_number"),
                        credit_score=int(row["credit_score"]),
                    )
                )

            has_credit_history = (
                session.query(CreditHistoryEntry).filter_by(customer_id=customer_id).first()
                is not None
            )
            if not has_credit_history:
                session.add_all(_backfill_credit_history(customer_id, int(row["credit_score"])))

            risk_score = row.get("risk_score")
            has_risk_history = (
                session.query(RiskScoreHistoryEntry).filter_by(customer_id=customer_id).first()
                is not None
            )
            if risk_score is not None and not has_risk_history:
                session.add_all(_backfill_risk_history(customer_id, float(risk_score)))

    print(f"Seeded {len(customers)} borrowers into Postgres.")


if __name__ == "__main__":
    run()
