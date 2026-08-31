from src.domain.entities import (
    AuditResult,
    CustomerProfile,
    RiskEvaluationResult,
    assess_behavioral_floor,
    explain_behavioral_verdict,
    parse_behavioral_assessment,
    reconcile_behavioral_assessment,
)
from src.domain.policy import UnderwritingPolicy
from src.infra.agents.agents import run_audit_committee
from src.infra.config import MODEL_PATH
from src.infra.database.database import (
    fetch_customer_by_id,
    fetch_customer_notes,
    record_audit_results,
)
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
        profile = CustomerProfile.from_db_record(customer, notes=raw_notes)

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

        # 6. Parse the committee's prose into a machine-actionable verdict.
        #    Deterministic policy outranks the model, so quant_standing is passed in.
        evaluation = RiskEvaluationResult.from_cro_report(
            reports.get("cro_decision", ""),
            quant_standing=quant_standing,
        )
        # The qualitative tier is checkable against the structured record, so the
        # model's reading is floored by deterministic policy the same way the CRO's
        # decision is floored by quant_standing above.
        model_assessment = parse_behavioral_assessment(reports.get("qual_analysis", ""))
        behavioral_floor, floor_reason = assess_behavioral_floor(
            profile.delinquencies, profile.employment_length_years
        )
        qual_assessment = reconcile_behavioral_assessment(model_assessment, behavioral_floor)

        # Each agent's verdict is stored with the reasoning that produced it. Where
        # policy overruled an agent, the stored report and the stored vote disagree
        # on their face; these lines are what make that legible downstream.
        bases = {
            "quant": (
                f"XGBoost default probability {risk_score * 100:.2f}% against policy "
                f"thresholds -> {quant_standing}."
            ),
            "qual": explain_behavioral_verdict(
                model_assessment, behavioral_floor, floor_reason, qual_assessment
            ),
            "cro": evaluation.explain(),
        }

        # 7. Persist the run so the dashboard reflects real audits, not fixtures.
        record_audit_results(
            customer_id=customer_id,
            requested_amount=profile.loan_amount,
            quant_standing=quant_standing,
            qual_assessment=qual_assessment,
            decision=evaluation.decision,
            risk_tier=evaluation.risk_tier,
            xgb_score=risk_score,
            reports=reports,
            timings_ms=reports.get("timings_ms", {}),
            bases=bases,
        )

        # 8. Build and return pure domain result
        return AuditResult(
            customer_id=customer_id,
            risk_score=risk_score,
            quant_standing=quant_standing,
            quant_report=reports.get("quant_analysis", ""),
            qual_report=reports.get("qual_analysis", ""),
            cro_report=reports.get("cro_decision", ""),
            decision=evaluation.decision,
            risk_tier=evaluation.risk_tier,
            qual_assessment=qual_assessment,
        )
