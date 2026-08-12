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

    @classmethod
    def from_db_record(cls, record: dict, notes: Optional[str] = None) -> "CustomerProfile":
        """Factory method to construct entity directly from DB query record."""
        return cls(
            customer_id=record["customer_id"],
            name=record.get("full_name", record.get("name", "")),
            credit_score=record["credit_score"],
            dti=float(record["debt_to_income_ratio"]),
            income=float(record["annual_income"]),
            loan_amount=float(record["loan_amount_requested"]),
            delinquencies=int(record["delinquencies_2yrs"]),
            cpf=record.get("cpf"),
            email=record.get("email"),
            phone_number=record.get("phone_number"),
            employment_length_years=record.get("employment_length_years"),
            is_high_risk=bool(record.get("is_high_risk", False)),
            notes=notes if notes is not None else record.get("notes")
        )

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