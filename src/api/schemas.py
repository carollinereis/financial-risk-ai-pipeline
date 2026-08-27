
from pydantic import BaseModel, ConfigDict


# ------------------------------------------------------------------
# Customer List Item (For dropdown / selector views)
# ------------------------------------------------------------------
class CustomerListItem(BaseModel):
    customer_id: int
    full_name: str
    credit_score: int
    risk_score: float | None = None


# ------------------------------------------------------------------
# Customer Financial Profile Response DTO
# ------------------------------------------------------------------
class CustomerProfileResponse(BaseModel):
    customer_id: int
    full_name: str
    credit_score: int
    debt_to_income_ratio: float
    annual_income: float
    loan_amount_requested: float
    delinquencies_2yrs: int
    employment_length_years: int | None = None
    live_xgb_risk_score: float
    cpf: str | None = None       # Sanitized / Masked PII
    email: str | None = None     # Sanitized / Masked PII
    sanitized_notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------
# Audit Committee Results Response DTO
# ------------------------------------------------------------------
class AuditResultResponse(BaseModel):
    customer_id: int
    quantitative_standing: str
    xgb_risk_score: float
    cro_decision: str
    quant_analysis: str
    qual_analysis: str
    # Structured verdict parsed from the CRO prose; additive, so existing
    # consumers of the free-text fields keep working unchanged.
    decision: str = "MANUAL REVIEW REQUIRED"
    risk_tier: str = "HIGH"
    qual_assessment: str = "MEDIUM"
