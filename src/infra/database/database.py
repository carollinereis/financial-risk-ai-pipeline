from pathlib import Path

import duckdb
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "financial_risk.duckdb"
CSV_PATH = DATA_DIR / "customers.csv"


def get_db_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH))

def get_read_connection() -> duckdb.DuckDBPyConnection:
    """Returns a read-only DuckDB connection for GET queries."""
    return duckdb.connect(str(DB_PATH), read_only=True)


def get_write_connection() -> duckdb.DuckDBPyConnection:
    """Returns a read-write DuckDB connection for INSERT/UPDATE queries."""
    return duckdb.connect(str(DB_PATH), read_only=False)


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


def fetch_customer_by_id(customer_id: int) -> dict | None:
    """Fetches a single customer record by ID as a dictionary."""
    with get_db_connection() as conn:
        result = conn.execute(
            "SELECT * FROM customers WHERE customer_id = $1", [customer_id]
        ).fetchone()

        if not result:
            return None

        columns = [desc[0] for desc in conn.description]
        return dict(zip(columns, result))

def fetch_customer_notes(customer_id: int) -> str | None:
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


def init_portfolio_tables():
    """Initializes extension tables for loan applications and AI agent evaluations."""
    with get_write_connection() as conn:
        conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_applications START 1")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_evaluations START 1")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_applications (
                application_id INTEGER PRIMARY KEY DEFAULT nextval('seq_applications'),
                customer_id INTEGER,
                requested_amount DECIMAL(12,2) NOT NULL,
                term_months INTEGER NOT NULL,
                decision_status VARCHAR DEFAULT 'IN_PROGRESS',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_evaluations (
                evaluation_id INTEGER PRIMARY KEY DEFAULT nextval('seq_evaluations'),
                application_id INTEGER,
                agent_name VARCHAR NOT NULL,
                decision VARCHAR NOT NULL,
                agent_score DECIMAL(5,2),
                rationale TEXT,
                execution_time_ms INTEGER,
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


def seed_sample_agent_analytics():
    """Seeds initial agent evaluations and loan requests for the dashboard."""
    with get_write_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM agent_evaluations").fetchone()[0]
        if count == 0:
            conn.execute("""
                INSERT INTO loan_applications (customer_id, requested_amount, term_months, decision_status)
                VALUES (101, 25000.00, 24, 'REJECTED');
            """)
            conn.execute("""
                INSERT INTO agent_evaluations (application_id, agent_name, decision, agent_score, execution_time_ms) VALUES
                (1, 'Quantitative Agent', 'REJECT', 16.07, 1100),
                (1, 'Qualitative Agent', 'REJECT', 45.0, 950),
                (1, 'CRO Decision Agent', 'ALERT', 10.0, 2100);
            """)


def fetch_executive_kpis() -> dict:
    """Executes aggregate queries over existing customer records and loan applications."""
    with get_read_connection() as conn:
        kpi_query = """
            SELECT 
                COUNT(a.application_id) AS total_applications,
                SUM(CASE WHEN a.decision_status = 'APPROVED' THEN 1 ELSE 0 END) AS total_approved,
                ROUND(COALESCE((SUM(CASE WHEN a.decision_status = 'APPROVED' THEN 1 ELSE 0 END) * 100.0) / NULLIF(COUNT(a.application_id), 0), 0), 2) AS approval_rate_pct,
                COALESCE(SUM(a.requested_amount), 0.0) AS total_requested_volume,
                COALESCE(SUM(CASE WHEN a.decision_status = 'APPROVED' THEN a.requested_amount ELSE 0 END), 0.0) AS approved_volume
            FROM loan_applications a;
        """
        res = conn.execute(kpi_query).fetchone()

        time_query = "SELECT ROUND(AVG(execution_time_ms) / 1000.0, 2) FROM agent_evaluations;"
        avg_time = conn.execute(time_query).fetchone()[0] or 0.0

        return {
            "total_applications": res[0] or 0,
            "total_approved": res[1] or 0,
            "approval_rate_pct": float(res[2] or 0.0),
            "total_requested_volume": float(res[3] or 0.0),
            "approved_volume": float(res[4] or 0.0),
            "avg_decision_time_sec": float(avg_time)
        }


def fetch_agent_divergence() -> list:
    """Fetches vote distributions across all AI agents for Recharts."""
    with get_read_connection() as conn:
        query = """
            SELECT 
                agent_name,
                decision,
                COUNT(*) AS total_decisions,
                ROUND(AVG(execution_time_ms), 0) AS avg_time_ms
            FROM agent_evaluations
            GROUP BY agent_name, decision
            ORDER BY agent_name;
        """
        df = conn.execute(query).df()
        return df.to_dict(orient="records")


if __name__ == "__main__":
    init_db()
    init_portfolio_tables()
    seed_sample_agent_analytics()
    sample = fetch_customer_by_id(101)
    print("\nSample DuckDB Query (Customer 101):")
    if sample:
        for key, value in sample.items():
            print(f"  {key}: {value}")
