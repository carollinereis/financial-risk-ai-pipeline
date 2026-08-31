from contextlib import asynccontextmanager

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.api.schemas import (
    AuditResultResponse,
    CustomerListItem,
    CustomerProfileResponse,
    CustomerRegistryItem,
    SavedAuditResponse,
)
from src.application.run_risk_audit import RunRiskAuditUseCase
from src.domain.policy import policy_reference
from src.infra.agents.agent_tools import (
    get_customer_financial_profile,
    get_sanitized_customer_notes,
)
from src.infra.config import DUCKDB_PATH
from src.infra.database.database import (
    fetch_agent_consensus_stats,
    fetch_agent_divergence,
    fetch_customer_registry,
    fetch_decision_distribution,
    fetch_executive_kpis,
    fetch_hitl_exception_queue,
    fetch_risk_profile_distribution,
    fetch_saved_audit,
    init_portfolio_tables,
    record_human_override,
    seed_sample_agent_analytics,
)


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
    lifespan=lifespan
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
        sanitized_notes=notes
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
    return SavedAuditResponse(**saved)


@app.post("/customers/{customer_id}/audit", response_model=AuditResultResponse)
def run_audit(customer_id: int):
    """Trigger multi-agent risk audit committee pipeline."""
    try:
        use_case = RunRiskAuditUseCase()
        result = use_case.execute(customer_id)

        # execute() returns a typed AuditResult, so read its attributes directly.
        # Pydantic validates the types at the response boundary.
        return AuditResultResponse(
            customer_id=result.customer_id,
            quantitative_standing=result.quant_standing,
            xgb_risk_score=result.risk_score,
            cro_decision=result.cro_report,
            quant_analysis=result.quant_report,
            qual_analysis=result.qual_report,
            decision=result.decision,
            risk_tier=result.risk_tier,
            qual_assessment=result.qual_assessment,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit execution error: {str(e)}") from e

# --- Executive Dashboard & AI Ops Endpoints ---
@app.get("/api/dashboard/kpis")
def get_dashboard_kpis():
    """Fetch high-level executive KPIs for the top card grid."""
    try:
        return fetch_executive_kpis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching executive KPIs: {str(e)}") from e


@app.get("/api/dashboard/customer-registry", response_model=list[CustomerRegistryItem])
def get_customer_registry():
    """Fetch every customer with the standing verdict and date of their last audit."""
    try:
        return fetch_customer_registry()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching customer registry: {str(e)}") from e


@app.get("/api/dashboard/agent-analytics")
def get_agent_analytics():
    """Fetch AI agent consensus/divergence distributions for Recharts."""
    try:
        return fetch_agent_divergence()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching agent analytics: {str(e)}") from e


@app.get("/api/dashboard/agent-consensus")
def get_agent_consensus():
    """Fetch unanimous vs divergent split driving the HITL exception workload."""
    try:
        return fetch_agent_consensus_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching agent consensus: {str(e)}") from e


@app.get("/api/dashboard/policy-reference")
def get_policy_reference():
    """Serves the enforced underwriting thresholds and the committee's policy list."""
    try:
        return policy_reference()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching policy reference: {str(e)}") from e


@app.get("/api/dashboard/decision-distribution")
def get_decision_distribution():
    """Fetch the portfolio outcome split (approved/rejected/manual review) for the donut."""
    try:
        return fetch_decision_distribution()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching decision distribution: {str(e)}") from e


@app.get("/api/dashboard/hitl-queue")
def get_hitl_queue():
    """Fetch applications where the agent committee disagreed, pending human review."""
    try:
        return fetch_hitl_exception_queue()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching HITL queue: {str(e)}") from e


@app.get("/api/dashboard/risk-profile")
def get_risk_profile():
    """Fetch portfolio rating bands, DTI-vs-default scatter, and delinquency matrix."""
    try:
        return fetch_risk_profile_distribution()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching risk profile: {str(e)}") from e


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
        raise HTTPException(status_code=422, detail="An override rationale is required for the audit trail.")

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
