from pathlib import Path
import duckdb
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "financial_risk.duckdb"
CSV_PATH = DATA_DIR / "customers.csv"


def get_db_connection() -> duckdb.DuckDBPyConnection:
    """Establishes and returns a connection to the DuckDB database."""
    return duckdb.connect(str(DB_PATH))


def init_db() -> None:
    """Initializes DuckDB and creates/refreshes the customers table directly from CSV."""
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

    print(f"√√ DuckDB initialized and populated with {count} records from '{CSV_PATH.name}'.")


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


if __name__ == "__main__":
    init_db()
    sample = fetch_customer_by_id(101)
    print("\nSample DuckDB Query (Customer 101):")
    if sample:
        for key, value in sample.items():
            print(f"  {key}: {value}")