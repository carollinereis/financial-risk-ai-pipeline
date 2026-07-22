import random
from pathlib import Path
from faker import Faker
import duckdb

fake = Faker()
Faker.seed(42)
random.seed(42)

DB_DIR = Path("data")
DB_PATH = DB_DIR / "financial_risk.db"


def init_db():
    """Initializes and seeds the DuckDB database with dynamic mock data and edge cases."""
    DB_DIR.mkdir(exist_ok=True)

    with duckdb.connect(str(DB_PATH)) as conn:
        print("Connected to DuckDB...")

        # 1. Create Tables (account_logs FIRST to avoid foreign key dependency errors)
        conn.execute("""
        CREATE OR REPLACE TABLE account_logs (
            log_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            log_date DATE,
            category VARCHAR,
            notes TEXT
        );
        """)

        conn.execute("""
        CREATE OR REPLACE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            full_name VARCHAR,
            annual_income DOUBLE,
            credit_score INTEGER,
            debt_to_income_ratio DOUBLE,
            delinquencies_2yrs INTEGER,
            loan_amount_requested DOUBLE,
            employment_length_years INTEGER
        );
        """)

        # 2. Build Customer Records
        customers = []

        # --- Specific Edge Cases ---
        # Edge Case 1: High Income, Low Credit Score (High earner mismanaging debt)
        customers.append((101, "Alice Smith", 210000.0, 580, 0.45, 2, 60000.0, 8))

        # Edge Case 2: Low Income, Perfect Credit Score (Reliable, low capacity)
        customers.append((102, "Bob Jones", 32000.0, 820, 0.15, 0, 10000.0, 5))

        # Edge Case 3: High-Risk Repeated Offender (Used later for multiple log entries)
        customers.append((103, "Carlos Silva", 45000.0, 510, 0.58, 6, 35000.0, 1))

        # Edge Case 4: Squeaky-clean customer (Will intentionally get 0 account logs)
        customers.append(
            (104, "Diana Prince", 115000.0, 790, 0.10, 0, 20000.0, 12)
        )

        # --- Generate 46 Random Customers to reach 50 total ---
        for cid in range(105, 151):
            income = round(random.uniform(28000, 180000), -2)
            score = random.randint(350, 850)
            dti = round(random.uniform(0.05, 0.65), 2)
            delinq = random.choices(
                [0, 1, 2, 3, 5], weights=[60, 20, 10, 7, 3]
            )[0]
            loan = round(random.uniform(5000, 75000), -2)
            emp_years = random.randint(0, 20)

            customers.append(
                (cid, fake.name(), income, score, dti, delinq, loan, emp_years)
            )

        # 3. Insert Customers
        conn.executemany(
            """
        INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
            customers,
        )

        # 4. Build Account Logs
        logs = []
        log_id = 1
        categories = [
            "Support",
            "Collections",
            "Risk Alert",
            "Wealth Management",
            "Underwriting",
        ]

        # Edge Case 3 Logs: Add 5 detailed history entries specifically for Carlos (103)
        carlos_history = [
            (
                "2026-01-15",
                "Support",
                "Inquired about payment extension due to missed paycheck.",
            ),
            (
                "2026-02-28",
                "Collections",
                "First notice: Overdue credit card balance by 30 days.",
            ),
            (
                "2026-04-10",
                "Collections",
                "Second notice: Account escalated to internal recovery unit.",
            ),
            (
                "2026-05-19",
                "Risk Alert",
                "High utilization flag triggered across multiple accounts.",
            ),
            (
                "2026-06-30",
                "Collections",
                "Customer requested restructured workout plan. Under review.",
            ),
        ]
        for date_str, cat, note in carlos_history:
            logs.append((log_id, 103, date_str, cat, note))
            log_id += 1

        # Add 1-2 standard logs for Alice (101) and Bob (102)
        logs.append(
            (
                log_id,
                101,
                "2026-03-12",
                "Risk Alert",
                "High income verified, but recent default on external auto loan.",
            )
        )
        log_id += 1
        logs.append(
            (
                log_id,
                102,
                "2026-05-01",
                "Support",
                "Inquired about small credit line expansion. Clean history.",
            )
        )
        log_id += 1

        # Note: Customer 104 (Diana) gets ZERO logs!

        # Generate logs for remaining random customers (giving ~60% of them logs)
        for cid in range(105, 151):
            if random.random() < 0.6:  # 60% chance of having notes
                num_notes = random.randint(1, 3)
                for _ in range(num_notes):
                    log_date = fake.date_between(
                        start_date="-1y", end_date="today"
                    )
                    cat = random.choice(categories)
                    note = fake.sentence(nb_words=12)
                    logs.append((log_id, cid, log_date, cat, note))
                    log_id += 1

        # 5. Insert Account Logs
        conn.executemany(
            """
        INSERT INTO account_logs VALUES (?, ?, ?, ?, ?);
        """,
            logs,
        )

        print(
            f"Successfully loaded {len(customers)} customers and {len(logs)} log records!"
        )


def verify_data():
    """Quick query to test our edge cases using a LEFT JOIN."""
    query = """
    SELECT 
        c.customer_id, 
        c.full_name, 
        c.annual_income, 
        c.credit_score, 
        COUNT(a.log_id) AS total_logs
    FROM customers c
    LEFT JOIN account_logs a ON c.customer_id = a.customer_id
    WHERE c.customer_id IN (101, 102, 103, 104)
    GROUP BY c.customer_id, c.full_name, c.annual_income, c.credit_score
    ORDER BY c.customer_id;
    """
    with duckdb.connect(str(DB_PATH)) as conn:
        results = conn.execute(query).fetchall()

    print("\n🔍 Verifying Edge Cases (LEFT JOIN Test):")
    print(
        f"{'ID':<5} | {'Name':<15} | {'Income':<10} | {'Score':<6} | {'Logs Count'}"
    )
    print("-" * 55)
    for cid, name, income, score, logs in results:
        print(
            f"{cid:<5} | {name:<15} | ${income:<9,.0f} | {score:<6} | {logs}"
        )


if __name__ == "__main__":
    init_db()
    verify_data()