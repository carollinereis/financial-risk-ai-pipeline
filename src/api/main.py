import uuid
from contextlib import asynccontextmanager

import duckdb
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.api.schemas import (
    AuditResultResponse,
    AuditTaskStartedResponse,
    AuditTaskStatusResponse,
    CustomerListItem,
    CustomerProfileResponse,
    CustomerRegistryItem,
    RiskScoreHistoryPoint,
    SavedAuditResponse,
    ScoreHistoryPoint,
)
from src.application.run_audit_task import run_audit_task
from src.domain.entities import extract_rationale
from src.domain.policy import policy_reference
from src.infra.agents.agent_tools import (
    get_customer_financial_profile,
    get_sanitized_customer_notes,
)
from src.infra.config import DUCKDB_PATH
from src.infra.database.database import (
    fetch_agent_consensus_stats,
    fetch_agent_divergence,
    fetch_credit_score_bands,
    fetch_customer_registry,
    fetch_decision_distribution,
    fetch_executive_kpis,
    fetch_hitl_exception_queue,
    fetch_portfolio_highlights,
    fetch_risk_profile_distribution,
    fetch_saved_audit,
    init_portfolio_tables,
    record_human_override,
    seed_sample_agent_analytics,
)
from src.infra.database.postgres.models import AuditTask, CreditHistoryEntry, RiskScoreHistoryEntry
from src.infra.database.postgres.session import get_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensures portfolio extension tables exist and seed data is loaded."""
    init_portfolio_tables()
    seed_sample_agent_analytics()
    yield


app = FastAPI(
    title="Financial Risk AI Pipeline API",
    description="Backend service exposing ML risk scores and Multi-Agent Audit evaluations.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Vite dev server (and local testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas for Dashboard Actions ---
# Underwriters may only settle a case one of two ways; anything else is rejected
# at the boundary so placeholder values can never reach decision_status.
ALLOWED_OVERRIDE_STATUSES = {"APPROVED", "REJECTED"}


class HumanOverrideRequest(BaseModel):
    status: str  # e.g., 'APPROVED' or 'REJECTED'
    rationale: str
    # Who is signing for the ruling. Self-declared: the dashboard has no auth, so
    # this attributes the decision without authenticating it. Required all the same
    # so no override can enter the trail anonymously.
    underwriter: str


def _fetch_or_500(fn, label: str):
    try:
        return fn()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching {label}: {str(e)}") from e


@app.get("/customers", response_model=list[CustomerListItem])
def list_customers():
    """Fetch available customer list for dropdown selection."""
    try:
        with duckdb.connect(str(DUCKDB_PATH), read_only=True) as conn:
            df = conn.execute(
                "SELECT customer_id, full_name, credit_score, risk_score "
                "FROM customers ORDER BY customer_id"
            ).df()
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e


@app.get("/customers/{customer_id}", response_model=CustomerProfileResponse)
def get_customer_profile(customer_id: int):
    """Fetch sanitized customer profile metrics and notes."""
    profile = get_customer_financial_profile(customer_id)
    if not profile or "error" in profile:
        raise HTTPException(status_code=404, detail=f"Customer ID {customer_id} not found.")

    notes = get_sanitized_customer_notes(customer_id)

    # Standardize output to match schema
    return CustomerProfileResponse(
        customer_id=profile["customer_id"],
        full_name=profile.get("full_name", ""),
        credit_score=profile["credit_score"],
        debt_to_income_ratio=float(profile["debt_to_income_ratio"]),
        annual_income=float(profile["annual_income"]),
        loan_amount_requested=float(profile["loan_amount_requested"]),
        delinquencies_2yrs=int(profile["delinquencies_2yrs"]),
        employment_length_years=profile.get("employment_length_years"),
        live_xgb_risk_score=float(profile.get("live_xgb_risk_score", 0.0)),
        cpf=profile.get("cpf"),
        email=profile.get("email"),
        phone_number=profile.get("phone_number"),
        cpf_masked=profile.get("cpf_masked"),
        email_masked=profile.get("email_masked"),
        phone_masked=profile.get("phone_masked"),
        sanitized_notes=notes,
    )


@app.get("/customers/{customer_id}/audit", response_model=SavedAuditResponse)
def get_saved_audit(customer_id: int):
    """Replay the stored committee transcript. Never invokes the agent pipeline."""
    try:
        saved = fetch_saved_audit(customer_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching saved audit: {str(e)}") from e

    if saved is None:
        raise HTTPException(
            status_code=404,
            detail=f"No saved audit recorded for customer ID {customer_id}.",
        )
    saved["rationale"] = extract_rationale(saved.get("cro_decision", ""))
    return SavedAuditResponse(**saved)


@app.post(
    "/customers/{customer_id}/audit", response_model=AuditTaskStartedResponse, status_code=202
)
def run_audit(customer_id: int, background_tasks: BackgroundTasks):
    """Kicks off the multi-agent risk audit committee pipeline in the background.

    The committee makes 3 sequential LLM calls (up to ~90s); running it inline blocked
    the whole request. This returns immediately with a task id the client polls via
    GET /tasks/{task_id} instead.
    """
    task_id = uuid.uuid4().hex
    with get_session() as session:
        session.add(AuditTask(id=task_id, customer_id=customer_id, status="PENDING"))

    background_tasks.add_task(run_audit_task, customer_id, task_id)
    return AuditTaskStartedResponse(task_id=task_id, status="PENDING")


@app.get("/tasks/{task_id}", response_model=AuditTaskStatusResponse)
def get_task_status(task_id: str):
    """Polling endpoint for an async audit task started via POST /customers/{id}/audit."""
    with get_session() as session:
        task = session.get(AuditTask, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")

        result = (
            AuditResultResponse.model_validate_json(task.result_json) if task.result_json else None
        )
        return AuditTaskStatusResponse(
            task_id=task.id,
            status=task.status,
            result=result,
            error=task.error,
        )


@app.get("/customers/{customer_id}/score-history", response_model=list[ScoreHistoryPoint])
def get_score_history(customer_id: int):
    """Fetches a borrower's historical credit-score points, chronologically."""
    with get_session() as session:
        entries = (
            session.query(CreditHistoryEntry)
            .filter(CreditHistoryEntry.customer_id == customer_id)
            .order_by(CreditHistoryEntry.recorded_at)
            .all()
        )
        return [
            ScoreHistoryPoint(date=entry.recorded_at.date().isoformat(), score=entry.score)
            for entry in entries
        ]


@app.get("/customers/{customer_id}/risk-score-history", response_model=list[RiskScoreHistoryPoint])
def get_risk_score_history(customer_id: int):
    """Fetches a borrower's XGBoost default-probability at each past audit run,
    chronologically. This is the only place that trend exists - DuckDB's
    agent_evaluations table deliberately keeps only the current run.
    """
    with get_session() as session:
        entries = (
            session.query(RiskScoreHistoryEntry)
            .filter(RiskScoreHistoryEntry.customer_id == customer_id)
            .order_by(RiskScoreHistoryEntry.recorded_at)
            .all()
        )
        return [
            RiskScoreHistoryPoint(date=entry.recorded_at.date().isoformat(), score=entry.score)
            for entry in entries
        ]


# --- Executive Dashboard & AI Ops Endpoints ---
@app.get("/api/dashboard/kpis")
def get_dashboard_kpis():
    """Fetch high-level executive KPIs for the top card grid."""
    return _fetch_or_500(fetch_executive_kpis, "executive KPIs")


@app.get("/api/dashboard/customer-registry", response_model=list[CustomerRegistryItem])
def get_customer_registry():
    """Fetch every customer with the standing verdict and date of their last audit."""
    return _fetch_or_500(fetch_customer_registry, "customer registry")


@app.get("/api/dashboard/agent-analytics")
def get_agent_analytics():
    """Fetch AI agent consensus/divergence distributions for Recharts."""
    return _fetch_or_500(fetch_agent_divergence, "agent analytics")


@app.get("/api/dashboard/agent-consensus")
def get_agent_consensus():
    """Fetch unanimous vs divergent split driving the HITL exception workload."""
    return _fetch_or_500(fetch_agent_consensus_stats, "agent consensus")


@app.get("/api/dashboard/policy-reference")
def get_policy_reference():
    """Serves the enforced underwriting thresholds and the committee's policy list."""
    return _fetch_or_500(policy_reference, "policy reference")


@app.get("/api/dashboard/decision-distribution")
def get_decision_distribution():
    """Fetch the portfolio outcome split (approved/rejected/manual review) for the donut."""
    return _fetch_or_500(fetch_decision_distribution, "decision distribution")


@app.get("/api/dashboard/hitl-queue")
def get_hitl_queue():
    """Fetch applications where the agent committee disagreed, pending human review."""
    return _fetch_or_500(fetch_hitl_exception_queue, "HITL queue")


@app.get("/api/dashboard/risk-profile")
def get_risk_profile():
    """Fetch portfolio rating bands, DTI-vs-default scatter, and delinquency matrix."""
    return _fetch_or_500(fetch_risk_profile_distribution, "risk profile")


@app.get("/api/dashboard/credit-score-bands")
def get_credit_score_bands():
    """Fetch average default probability grouped by FICO credit-score tier."""
    return _fetch_or_500(fetch_credit_score_bands, "credit score bands")


@app.get("/api/dashboard/portfolio-highlights")
def get_portfolio_highlights(limit: int = 5):
    """Fetch the top-N default-risk and largest-loan clients, plus portfolio averages."""
    return _fetch_or_500(lambda: fetch_portfolio_highlights(limit=limit), "portfolio highlights")


@app.patch("/api/dashboard/override/{application_id}")
def override_human_decision(application_id: int, payload: HumanOverrideRequest):
    """Allows an underwriter to manually approve/reject flagged cases in the HITL queue."""
    status = payload.status.strip().upper()
    if status not in ALLOWED_OVERRIDE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{payload.status}'. Expected one of: {sorted(ALLOWED_OVERRIDE_STATUSES)}.",
        )

    rationale = payload.rationale.strip()
    if not rationale:
        raise HTTPException(
            status_code=422, detail="An override rationale is required for the audit trail."
        )

    underwriter = payload.underwriter.strip()
    if not underwriter:
        raise HTTPException(
            status_code=422,
            detail="An underwriter name is required so the override is attributable.",
        )

    try:
        record_human_override(application_id, status, rationale, underwriter)

        return {
            "message": "Decision successfully updated",
            "application_id": application_id,
            "new_status": status,
            "overridden_by": underwriter,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating decision: {str(e)}") from e
