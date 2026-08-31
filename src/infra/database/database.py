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
        return dict(zip(columns, result, strict=True))

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

        # Added after the initial schema; ALTER keeps pre-existing databases in step.
        conn.execute("ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS override_notes TEXT;")
        conn.execute("ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS overridden_at TIMESTAMP;")


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

        # Exposure-weighted portfolio risk: large loans move the average more than small ones.
        risk_query = """
            SELECT ROUND(
                COALESCE(
                    SUM(risk_score * loan_amount_requested) / NULLIF(SUM(loan_amount_requested), 0),
                    0.0
                ), 4)
            FROM customers
            WHERE risk_score IS NOT NULL;
        """
        weighted_risk = conn.execute(risk_query).fetchone()[0] or 0.0

        return {
            "total_applications": res[0] or 0,
            "total_approved": res[1] or 0,
            "approval_rate_pct": float(res[2] or 0.0),
            "total_requested_volume": float(res[3] or 0.0),
            "approved_volume": float(res[4] or 0.0),
            "avg_decision_time_sec": float(avg_time),
            "weighted_avg_risk_score": float(weighted_risk)
        }


# Canonical committee outcomes. Emitted even at zero so the donut keeps stable
# slices, and MANUAL REVIEW REQUIRED stays visible as its own portfolio state.
DECISION_STATUSES = ["APPROVED", "REJECTED", "MANUAL REVIEW REQUIRED"]


def fetch_decision_distribution() -> dict:
    """Portfolio outcome split over the persisted decision, honouring human overrides."""
    with get_read_connection() as conn:
        query = """
            SELECT
                COALESCE(decision_status, 'IN_PROGRESS') AS status,
                COUNT(*) AS application_count,
                COALESCE(SUM(CASE WHEN overridden_at IS NOT NULL THEN 1 ELSE 0 END), 0) AS overridden_count,
                CAST(COALESCE(SUM(requested_amount), 0) AS DOUBLE) AS total_exposure
            FROM loan_applications
            GROUP BY status;
        """
        rows = {row["status"]: row for row in conn.execute(query).df().to_dict(orient="records")}
        total = sum(int(row["application_count"]) for row in rows.values())

        # Any status the pipeline writes that is not canonical (IN_PROGRESS, or a
        # future state) is appended rather than silently dropped from the total.
        ordered = DECISION_STATUSES + sorted(set(rows) - set(DECISION_STATUSES))

        distribution = [
            {
                "status": status,
                "application_count": int(rows.get(status, {}).get("application_count", 0)),
                "overridden_count": int(rows.get(status, {}).get("overridden_count", 0)),
                "total_exposure": float(rows.get(status, {}).get("total_exposure") or 0.0),
                "share_pct": round(
                    (int(rows.get(status, {}).get("application_count", 0)) * 100.0) / total, 2
                )
                if total
                else 0.0,
            }
            for status in ordered
        ]

        return {
            "total_applications": total,
            "distribution": distribution,
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


def fetch_agent_consensus_stats() -> dict:
    """Aggregates unanimous vs divergent applications to size the HITL workload."""
    with get_read_connection() as conn:
        query = """
            WITH per_application AS (
                SELECT application_id, COUNT(DISTINCT decision) AS distinct_decisions
                FROM agent_evaluations
                GROUP BY application_id
            )
            SELECT
                COUNT(*) AS evaluated_applications,
                COALESCE(SUM(CASE WHEN p.distinct_decisions = 1 THEN 1 ELSE 0 END), 0) AS unanimous,
                COALESCE(SUM(CASE WHEN p.distinct_decisions > 1 THEN 1 ELSE 0 END), 0) AS divergent,
                COALESCE(SUM(
                    CASE WHEN p.distinct_decisions > 1 AND a.overridden_at IS NULL THEN 1 ELSE 0 END
                ), 0) AS pending_review
            FROM per_application p
            LEFT JOIN loan_applications a ON a.application_id = p.application_id;
        """
        res = conn.execute(query).fetchone()

        evaluated = res[0] or 0
        unanimous = res[1] or 0
        divergent = res[2] or 0
        pending_review = res[3] or 0
        divergence_rate = round((divergent * 100.0) / evaluated, 2) if evaluated else 0.0

        return {
            "evaluated_applications": evaluated,
            "unanimous_count": unanimous,
            "divergent_count": divergent,
            # Divergence is a standing fact about agent behaviour; pending_review is the
            # subset a human has not yet ruled on, so it drains as the queue is worked.
            "pending_review_count": pending_review,
            "consensus_rate_pct": round(100.0 - divergence_rate, 2) if evaluated else 0.0,
            "divergence_rate_pct": divergence_rate,
        }


def fetch_hitl_exception_queue() -> list:
    """Lists applications whose agents disagreed, with each agent's vote attached."""
    with get_read_connection() as conn:
        queue_query = """
            WITH per_application AS (
                SELECT application_id, COUNT(DISTINCT decision) AS distinct_decisions
                FROM agent_evaluations
                GROUP BY application_id
            )
            SELECT
                a.application_id,
                a.customer_id,
                COALESCE(c.full_name, 'Unknown Customer') AS full_name,
                CAST(a.requested_amount AS DOUBLE) AS requested_amount,
                a.term_months,
                a.decision_status,
                a.created_at
            FROM loan_applications a
            JOIN per_application p ON p.application_id = a.application_id
            LEFT JOIN customers c ON c.customer_id = a.customer_id
            WHERE p.distinct_decisions > 1
              AND a.overridden_at IS NULL
            ORDER BY a.created_at DESC;
        """
        applications = conn.execute(queue_query).df().to_dict(orient="records")
        if not applications:
            return []

        votes_query = """
            SELECT
                application_id,
                agent_name,
                decision,
                CAST(agent_score AS DOUBLE) AS agent_score,
                rationale,
                execution_time_ms
            FROM agent_evaluations
            WHERE application_id IN (
                SELECT application_id FROM agent_evaluations
                GROUP BY application_id HAVING COUNT(DISTINCT decision) > 1
            )
            ORDER BY application_id, agent_name;
        """
        votes = conn.execute(votes_query).df().to_dict(orient="records")

        # Single pass groups votes by application so the queue stays one round-trip.
        votes_by_application: dict[int, list] = {}
        for vote in votes:
            votes_by_application.setdefault(int(vote["application_id"]), []).append(vote)

        for application in applications:
            application_id = int(application["application_id"])
            application["created_at"] = str(application["created_at"])
            application["agent_votes"] = votes_by_application.get(application_id, [])

        return applications


# The registry and the saved-report view both read the customer's most recent
# application; a re-audit rewrites that row's verdicts in place, so "latest
# application" and "current standing" are the same record.
LATEST_APPLICATION_CTE = """
    WITH latest_application AS (
        SELECT application_id, customer_id, decision_status, overridden_at, created_at
        FROM (
            SELECT
                application_id, customer_id, decision_status, overridden_at, created_at,
                ROW_NUMBER() OVER (
                    PARTITION BY customer_id ORDER BY created_at DESC, application_id DESC
                ) AS recency_rank
            FROM loan_applications
        )
        WHERE recency_rank = 1
    )
"""


def fetch_customer_registry() -> list:
    """Lists every customer with the standing verdict of their latest audit, if any.

    Read-only by construction: the pipeline is never triggered from here, so the
    registry can be opened on the whole portfolio without spending an LLM call.
    """
    with get_read_connection() as conn:
        registry_query = (
            LATEST_APPLICATION_CTE
            + """
            SELECT
                c.customer_id,
                c.full_name,
                c.credit_score,
                CAST(c.risk_score AS DOUBLE) AS risk_score,
                a.application_id,
                a.decision_status,
                a.overridden_at IS NOT NULL AS human_overridden,
                e.cro_verdict,
                e.last_analyzed_at,
                e.agent_count
            FROM customers c
            LEFT JOIN latest_application a ON a.customer_id = c.customer_id
            LEFT JOIN (
                SELECT
                    application_id,
                    MAX(evaluated_at) AS last_analyzed_at,
                    COUNT(*) AS agent_count,
                    MAX(CASE WHEN agent_name = 'CRO Decision Agent' THEN decision END) AS cro_verdict
                FROM agent_evaluations
                GROUP BY application_id
            ) e ON e.application_id = a.application_id
            ORDER BY c.customer_id
        """
        )
        rows = conn.execute(registry_query).df().to_dict(orient="records")

    for row in rows:
        application_id = row.get("application_id")
        last_analyzed = row.get("last_analyzed_at")
        # A customer with no application has never faced the committee; the UI
        # shows "Not analyzed" rather than an empty verdict cell.
        row["application_id"] = None if pd.isna(application_id) else int(application_id)
        row["has_saved_audit"] = bool(row["application_id"]) and int(row.get("agent_count") or 0) > 0
        row["last_analyzed_at"] = None if pd.isna(last_analyzed) else str(last_analyzed)
        row["decision_status"] = None if pd.isna(row.get("decision_status")) else row["decision_status"]
        row["cro_verdict"] = None if pd.isna(row.get("cro_verdict")) else row["cro_verdict"]
        row["human_overridden"] = bool(row.get("human_overridden"))
        row["risk_score"] = None if pd.isna(row.get("risk_score")) else float(row["risk_score"])
        row.pop("agent_count", None)

    return rows


def fetch_saved_audit(customer_id: int) -> dict | None:
    """Returns the persisted committee transcript for a customer's latest application.

    Returns None when no run has been recorded, which the API surfaces as a 404 so
    the dashboard can offer a first run instead of rendering an empty report.
    """
    with get_read_connection() as conn:
        application = conn.execute(
            """
            SELECT application_id, decision_status, override_notes, overridden_at, created_at
            FROM loan_applications
            WHERE customer_id = ?
            ORDER BY created_at DESC, application_id DESC
            LIMIT 1
            """,
            [customer_id],
        ).fetchone()
        if not application:
            return None

        application_id = int(application[0])
        evaluations = conn.execute(
            """
            SELECT
                agent_name,
                decision,
                CAST(agent_score AS DOUBLE) AS agent_score,
                rationale,
                execution_time_ms,
                evaluated_at
            FROM agent_evaluations
            WHERE application_id = ?
            ORDER BY agent_name
            """,
            [application_id],
        ).fetchall()

    if not evaluations:
        return None

    by_agent = {row[0]: row for row in evaluations}
    quant = by_agent.get("Quantitative Agent")
    qual = by_agent.get("Qualitative Agent")
    cro = by_agent.get("CRO Decision Agent")

    return {
        "customer_id": customer_id,
        "application_id": application_id,
        "decision": application[1] or "MANUAL REVIEW REQUIRED",
        "human_overridden": application[3] is not None,
        "override_notes": application[2],
        "last_analyzed_at": str(max(row[5] for row in evaluations)),
        # Scores are persisted as percentages; the live audit response reports the
        # XGBoost probability on a 0-1 scale, so convert back for one shared shape.
        "xgb_risk_score": (quant[2] / 100.0) if quant and quant[2] is not None else 0.0,
        "quant_verdict": quant[1] if quant else None,
        "qual_verdict": qual[1] if qual else None,
        "cro_verdict": cro[1] if cro else None,
        "quant_analysis": (quant[3] if quant else "") or "",
        "qual_analysis": (qual[3] if qual else "") or "",
        "cro_decision": (cro[3] if cro else "") or "",
        "execution_time_ms": sum(int(row[4] or 0) for row in evaluations),
    }


def record_human_override(application_id: int, status: str, rationale: str) -> None:
    """Persists an underwriter decision together with its audit rationale."""
    with get_write_connection() as conn:
        conn.execute("""
            UPDATE loan_applications
            SET decision_status = ?,
                override_notes = ?,
                overridden_at = CURRENT_TIMESTAMP
            WHERE application_id = ?
        """, [status, rationale, application_id])


# Default-probability bands, lowest risk first. Upper bound is exclusive so the
# ranges tile the 0-1 interval without gaps or overlap.
RISK_BANDS = [
    ("A", 0.00, 0.05),
    ("B", 0.05, 0.15),
    ("C", 0.15, 0.30),
    ("D", 0.30, 0.50),
    ("E", 0.50, 0.75),
    ("F", 0.75, 1.01),
]


def fetch_risk_profile_distribution() -> dict:
    """Portfolio risk shape: rating bands, DTI-vs-default scatter, delinquency matrix."""
    with get_read_connection() as conn:
        band_case = " ".join(
            f"WHEN risk_score >= {low} AND risk_score < {high} THEN '{label}'"
            for label, low, high in RISK_BANDS
        )

        bands_query = f"""
            SELECT
                CASE {band_case} ELSE 'F' END AS band,
                COUNT(*) AS customer_count,
                ROUND(AVG(risk_score), 4) AS avg_risk_score,
                CAST(COALESCE(SUM(loan_amount_requested), 0) AS DOUBLE) AS total_exposure
            FROM customers
            WHERE risk_score IS NOT NULL
            GROUP BY band
            ORDER BY band;
        """
        band_rows = {row["band"]: row for row in conn.execute(bands_query).df().to_dict(orient="records")}

        # Emit every band even when empty so the chart keeps a stable A-F axis.
        rating_bands = [
            {
                "band": label,
                "range_label": f"{low:.0%}-{min(high, 1.0):.0%}",
                "customer_count": int(band_rows.get(label, {}).get("customer_count", 0)),
                "avg_risk_score": float(band_rows.get(label, {}).get("avg_risk_score") or 0.0),
                "total_exposure": float(band_rows.get(label, {}).get("total_exposure") or 0.0),
            }
            for label, low, high in RISK_BANDS
        ]

        dti_query = """
            SELECT
                customer_id,
                ROUND(debt_to_income_ratio, 4) AS debt_to_income_ratio,
                ROUND(risk_score, 4) AS risk_score,
                credit_score,
                delinquencies_2yrs
            FROM customers
            WHERE risk_score IS NOT NULL AND debt_to_income_ratio IS NOT NULL
            ORDER BY debt_to_income_ratio;
        """
        dti_relationship = conn.execute(dti_query).df().to_dict(orient="records")

        delinquency_query = """
            SELECT
                delinquencies_2yrs,
                COUNT(*) AS customer_count,
                ROUND(AVG(risk_score), 4) AS avg_risk_score,
                COALESCE(SUM(CASE WHEN is_high_risk = 1 THEN 1 ELSE 0 END), 0) AS high_risk_count,
                CAST(COALESCE(SUM(loan_amount_requested), 0) AS DOUBLE) AS total_exposure
            FROM customers
            WHERE risk_score IS NOT NULL
            GROUP BY delinquencies_2yrs
            ORDER BY delinquencies_2yrs;
        """
        delinquency_matrix = conn.execute(delinquency_query).df().to_dict(orient="records")

        return {
            "rating_bands": rating_bands,
            "dti_relationship": dti_relationship,
            "delinquency_matrix": delinquency_matrix,
        }


# The dashboard charts group on these three verdicts, so each agent's native
# vocabulary is mapped onto them before it is stored.
QUANT_STANDING_TO_VERDICT = {
    "CRITICAL RISK": "REJECT",
    "MODERATE RISK": "ALERT",
    "LOW RISK": "APPROVE",
}
# INSUFFICIENT DATA votes ALERT, never APPROVE: an unverifiable file is routed to
# a human rather than counted as a clean one.
QUAL_ASSESSMENT_TO_VERDICT = {
    "HIGH": "REJECT",
    "MEDIUM": "ALERT",
    "INSUFFICIENT DATA": "ALERT",
    "LOW": "APPROVE",
}
CRO_DECISION_TO_VERDICT = {
    "REJECTED": "REJECT",
    "APPROVED": "APPROVE",
    "MANUAL REVIEW REQUIRED": "ALERT",
}
# agent_score is a 0-100 risk reading where higher means riskier.
QUAL_ASSESSMENT_TO_SCORE = {
    "LOW": 10.0,
    "MEDIUM": 50.0,
    "INSUFFICIENT DATA": 50.0,
    "HIGH": 90.0,
}
CRO_TIER_TO_SCORE = {"LOW": 10.0, "MEDIUM": 40.0, "HIGH": 70.0, "EXTREME": 95.0}


def resolve_application_id(conn, customer_id: int, requested_amount: float) -> int:
    """Returns the customer's latest application, opening one if none exists yet."""
    existing = conn.execute(
        """
        SELECT application_id FROM loan_applications
        WHERE customer_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        [customer_id],
    ).fetchone()
    if existing:
        return int(existing[0])

    conn.execute(
        """
        INSERT INTO loan_applications (customer_id, requested_amount, term_months, decision_status)
        VALUES (?, ?, ?, 'IN_PROGRESS')
        """,
        [customer_id, requested_amount, 24],
    )
    return int(
        conn.execute(
            "SELECT MAX(application_id) FROM loan_applications WHERE customer_id = ?",
            [customer_id],
        ).fetchone()[0]
    )


def record_audit_results(
    customer_id: int,
    requested_amount: float,
    quant_standing: str,
    qual_assessment: str,
    decision: str,
    risk_tier: str,
    xgb_score: float,
    reports: dict,
    timings_ms: dict,
) -> dict:
    """Persists one committee run: three agent verdicts plus the resulting status."""
    with get_write_connection() as conn:
        application_id = resolve_application_id(conn, customer_id, requested_amount)

        # A re-audit replaces the previous verdicts; the dashboard reports current
        # standing, and appending would double-count in the divergence stats.
        conn.execute("DELETE FROM agent_evaluations WHERE application_id = ?", [application_id])

        rows = [
            (
                application_id,
                "Quantitative Agent",
                QUANT_STANDING_TO_VERDICT.get(quant_standing, "ALERT"),
                round(xgb_score * 100, 2),
                reports.get("quant_analysis", ""),
                int(timings_ms.get("quant", 0)),
            ),
            (
                application_id,
                "Qualitative Agent",
                QUAL_ASSESSMENT_TO_VERDICT.get(qual_assessment, "ALERT"),
                QUAL_ASSESSMENT_TO_SCORE.get(qual_assessment, 50.0),
                reports.get("qual_analysis", ""),
                int(timings_ms.get("qual", 0)),
            ),
            (
                application_id,
                "CRO Decision Agent",
                CRO_DECISION_TO_VERDICT.get(decision, "ALERT"),
                CRO_TIER_TO_SCORE.get(risk_tier, 70.0),
                reports.get("cro_decision", ""),
                int(timings_ms.get("cro", 0)),
            ),
        ]
        conn.executemany(
            """
            INSERT INTO agent_evaluations
                (application_id, agent_name, decision, agent_score, rationale, execution_time_ms)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        # A human ruling is final: never let a later re-audit overwrite it.
        overridden = conn.execute(
            "SELECT overridden_at FROM loan_applications WHERE application_id = ?",
            [application_id],
        ).fetchone()

        status_written = overridden is None or overridden[0] is None
        if status_written:
            conn.execute(
                "UPDATE loan_applications SET decision_status = ? WHERE application_id = ?",
                [decision, application_id],
            )

        return {
            "application_id": application_id,
            "decision_status_written": status_written,
        }


if __name__ == "__main__":
    init_db()
    init_portfolio_tables()
    seed_sample_agent_analytics()
    sample = fetch_customer_by_id(101)
    print("\nSample DuckDB Query (Customer 101):")
    if sample:
        for key, value in sample.items():
            print(f"  {key}: {value}")
