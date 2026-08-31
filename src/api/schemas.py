
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


# ------------------------------------------------------------------
# Evaluated Customers Registry Row DTO
# ------------------------------------------------------------------
class CustomerRegistryItem(BaseModel):
    customer_id: int
    full_name: str
    credit_score: int
    risk_score: float | None = None
    application_id: int | None = None
    # Standing verdict on the latest application; null until the committee has run.
    decision_status: str | None = None
    cro_verdict: str | None = None
    human_overridden: bool = False
    overridden_by: str | None = None
    last_analyzed_at: str | None = None
    has_saved_audit: bool = False
    # True when the three agents did not agree, so policy rather than consensus
    # settled the file.
    committee_split: bool = False
    # The XGBoost probability as it stood when the committee ran. Divergence from
    # risk_score means the model has re-scored the client since.
    audit_risk_score: float | None = None


# ------------------------------------------------------------------
# Persisted Audit Transcript DTO (read-only replay, no pipeline run)
# ------------------------------------------------------------------
class SavedAuditResponse(BaseModel):
    customer_id: int
    application_id: int
    decision: str
    human_overridden: bool = False
    override_notes: str | None = None
    overridden_by: str | None = None
    overridden_at: str | None = None
    last_analyzed_at: str | None = None
    xgb_risk_score: float = 0.0
    quant_verdict: str | None = None
    qual_verdict: str | None = None
    cro_verdict: str | None = None
    quant_analysis: str = ""
    qual_analysis: str = ""
    cro_decision: str = ""
    # One line per agent explaining how the verdict was reached, including any
    # deterministic policy override that contradicts the agent's own prose.
    quant_basis: str | None = None
    qual_basis: str | None = None
    cro_basis: str | None = None
    execution_time_ms: int = 0
