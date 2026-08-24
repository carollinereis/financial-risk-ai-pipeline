import duckdb
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.infra.config import DUCKDB_PATH
from src.infra.agents.agent_tools import (
    get_customer_financial_profile,
    get_sanitized_customer_notes
)
from src.application.run_risk_audit import RunRiskAuditUseCase
from src.api.schemas import (
    CustomerListItem,
    CustomerProfileResponse,
    AuditResultResponse
)
from src.infra.database.database import (
    init_portfolio_tables,
    seed_sample_agent_analytics,
    fetch_executive_kpis,
    fetch_agent_divergence,
    get_write_connection
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
class HumanOverrideRequest(BaseModel):
    status: str  # e.g., 'APPROVED' or 'REJECTED'
    rationale: str

@app.get("/customers", response_model=List[CustomerListItem])
def list_customers():
    """Fetch available customer list for dropdown selection."""
    try:
        with duckdb.connect(str(DUCKDB_PATH), read_only=True) as conn:
            df = conn.execute("SELECT customer_id, full_name FROM customers ORDER BY customer_id").df()
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


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
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit execution error: {str(e)}")
    
# --- Executive Dashboard & AI Ops Endpoints ---
@app.get("/api/dashboard/kpis")
def get_dashboard_kpis():
    """Fetch high-level executive KPIs for the top card grid."""
    try:
        return fetch_executive_kpis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching executive KPIs: {str(e)}")


@app.get("/api/dashboard/agent-analytics")
def get_agent_analytics():
    """Fetch AI agent consensus/divergence distributions for Recharts."""
    try:
        return fetch_agent_divergence()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching agent analytics: {str(e)}")


@app.patch("/api/dashboard/override/{application_id}")
def override_human_decision(application_id: int, payload: HumanOverrideRequest):
    """Allows an underwriter to manually approve/reject flagged cases in the HITL queue."""
    try:
        with get_write_connection() as conn:
            conn.execute("""
                UPDATE loan_applications 
                SET decision_status = ? 
                WHERE application_id = ?
            """, [payload.status, application_id])
            
        return {
            "message": "Decision successfully updated",
            "application_id": application_id,
            "new_status": payload.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating decision: {str(e)}")