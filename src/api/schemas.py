from typing import Optional
from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Customer List Item (For dropdown / selector views)
# ------------------------------------------------------------------
class CustomerListItem(BaseModel):
    customer_id: int
    full_name: str


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
    employment_length_years: Optional[int] = None
    live_xgb_risk_score: float
    cpf: Optional[str] = None       # Sanitized / Masked PII
    email: Optional[str] = None     # Sanitized / Masked PII
    sanitized_notes: Optional[str] = None

    class Config:
        from_attributes = True


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