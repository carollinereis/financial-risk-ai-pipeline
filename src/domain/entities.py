from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class CustomerProfile:
    customer_id: int
    name: str
    credit_score: int
    dti: float
    income: float
    loan_amount: float
    delinquencies: int
    cpf: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    employment_length_years: Optional[int] = None
    is_high_risk: Optional[bool] = False
    notes: Optional[str] = None

@dataclass
class RiskEvaluationResult:
    decision: str  # APPROVED, REJECTED, MANUAL REVIEW REQUIRED
    risk_tier: str # LOW, MODERATE, CRITICAL RISK
    rationale: str


@dataclass
class AuditResult:
    """Represents the complete output of the multi-agent risk audit committee."""
    customer_id: int
    risk_score: float
    quant_standing: str
    quant_report: str
    qual_report: str
    cro_report: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "risk_score": self.risk_score,
            "quant_standing": self.quant_standing,
            "quant_report": self.quant_report,
            "qual_report": self.qual_report,
            "cro_report": self.cro_report,
        }