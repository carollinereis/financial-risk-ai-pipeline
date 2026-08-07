from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "financial_risk.duckdb"
CSV_PATH = DATA_DIR / "customers.csv"


def get_db_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH))


def init_db() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"CSV file not found at {CSV_PATH}. Please run 'python src/generate_data.py' first!"
        )

    with get_db_connection() as conn:
        conn.execute(
            "CREATE OR REPLACE TABLE customers AS SELECT * FROM read_csv_auto(?)",
            [str(CSV_PATH)],
        )
        count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]

    print(f"√ DuckDB initialized and populated with {count} records from '{CSV_PATH.name}'.")


def fetch_customer_by_id(customer_id: int) -> Optional[dict]:
    """Fetches a single customer record by ID as a dictionary."""
    with get_db_connection() as conn:
        result = conn.execute(
            "SELECT * FROM customers WHERE customer_id = $1", [customer_id]
        ).fetchone()

        if not result:
            return None

        columns = [desc[0] for desc in conn.description]
        return dict(zip(columns, result))

def fetch_customer_notes(customer_id: int) -> Optional[str]:
    """Fetches the raw (unsanitized) underwriter notes for a single customer."""
    with get_db_connection() as conn:
        result = conn.execute(
            "SELECT underwriter_notes FROM customers WHERE customer_id = $1",
            [customer_id],
        ).fetchone()

    return result[0] if result and result[0] else None

def ensure_risk_columns(conn) -> None:
    """Schema migration helper for ML risk scores."""
    conn.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS risk_score DOUBLE;")
    conn.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS is_high_risk_predicted BOOLEAN;")
    conn.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS model_version VARCHAR;")
    conn.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS scored_at TIMESTAMP;")


def bulk_update_risk_scores(conn, df: pd.DataFrame) -> None:
    """Fast bulk persistence using DuckDB relation joins."""
    ensure_risk_columns(conn)

    conn.register(
        "scores_tmp",
        df[["customer_id", "risk_score", "is_high_risk_predicted", "model_version", "scored_at"]],
    )
    conn.execute("""
        UPDATE customers SET
            risk_score = scores_tmp.risk_score,
            is_high_risk_predicted = scores_tmp.is_high_risk_predicted,
            model_version = scores_tmp.model_version,
            scored_at = scores_tmp.scored_at
        FROM scores_tmp
        WHERE customers.customer_id = scores_tmp.customer_id
    """)
    print("√ Bulk updated predictions into DuckDB!")


def get_high_risk_customers() -> pd.DataFrame:
    """Trigger query for Phase 4 LLM Reasoning Agents."""
    with get_db_connection() as conn:
        return conn.execute("""
            SELECT customer_id, full_name, risk_score, underwriter_notes
            FROM customers
            WHERE is_high_risk_predicted = TRUE
            ORDER BY risk_score DESC
        """).df()


if __name__ == "__main__":
    init_db()
    sample = fetch_customer_by_id(101)
    print("\nSample DuckDB Query (Customer 101):")
    if sample:
        for key, value in sample.items():
            print(f"  {key}: {value}")
