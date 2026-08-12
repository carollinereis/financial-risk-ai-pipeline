import duckdb
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(
    title="Financial Risk AI Pipeline API",
    description="Backend service exposing ML risk scores and Multi-Agent Audit evaluations.",
    version="1.0.0"
)

# Enable CORS for Vite dev server (and local testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        
        # If result is an object/dataclass, read attributes; otherwise read dict keys
        def get_val(obj, attr, default=""):
            if isinstance(obj, dict):
                return obj.get(attr, default)
            return getattr(obj, attr, default)

        return AuditResultResponse(
            customer_id=customer_id,
            quantitative_standing=str(get_val(result, "quant_standing", get_val(result, "quant_standing", "CRITICAL RISK"))),
            xgb_risk_score=float(get_val(result, "xgb_score", get_val(result, "xgb_risk_score", 0.0))),
            cro_decision=str(get_val(result, "cro_report", get_val(result, "cro_decision", "No decision rendered."))),
            quant_analysis=str(get_val(result, "quant_report", "")),
            qual_analysis=str(get_val(result, "qual_report", ""))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit execution error: {str(e)}")