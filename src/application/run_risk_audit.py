from src.domain.entities import AuditResult, CustomerProfile
from src.domain.policy import UnderwritingPolicy
from src.infra.agents.agents import run_audit_committee
from src.infra.config import DUCKDB_PATH, MODEL_PATH
from src.infra.database.database import fetch_customer_by_id, fetch_customer_notes
from src.infra.ml.credit_risk_model import CreditRiskModel
from src.infra.security.security import sanitize_input


class RunRiskAuditUseCase:
    """Orchestrates the complete credit risk evaluation workflow."""

    def __init__(self):
        self.ml_model = CreditRiskModel.load_model(MODEL_PATH)

    def execute(self, customer_id: int) -> AuditResult:
        # 1. Ingest customer data from database layer
        customer = fetch_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer ID {customer_id} not found.")

        raw_notes = fetch_customer_notes(customer_id)

        # 2. Map raw DB dict -> Domain Entity
        profile = CustomerProfile(
            customer_id=customer["customer_id"],
            name=customer["full_name"],
            credit_score=customer["credit_score"],
            dti=customer["debt_to_income_ratio"],
            income=customer["annual_income"],
            loan_amount=customer["loan_amount_requested"],
            delinquencies=customer["delinquencies_2yrs"],
            employment_length_years=customer.get("employment_length_years"),
            notes=raw_notes,
        )

        # 3. Sanitize unstructured text inputs
        sanitized_notes = sanitize_input(profile.notes) if profile.notes else ""

        # 4. Calculate risk score and quantitative standing
        risk_score = self.ml_model.predict_risk(profile)

        quant_standing = UnderwritingPolicy.evaluate_quantitative_standing(
            credit_score=profile.credit_score,
            dti=profile.dti,
            xgb_score=risk_score,
        )

        # 5. Run 3-agent committee pipeline
        reports = run_audit_committee(
            profile=profile,
            xgb_score=risk_score,
            sanitized_notes=sanitized_notes,
            quant_standing=quant_standing,
        )

        # 6. Build and return pure domain result
        return AuditResult(
            customer_id=customer_id,
            risk_score=risk_score,
            quant_standing=quant_standing,
            quant_report=reports.get("quant_analysis", ""),
            qual_report=reports.get("qual_analysis", ""),
            cro_report=reports.get("cro_decision", ""),
        )