"""Unit tests for parsing agent prose into structured verdicts.

These are pure-logic tests: no database, no LLM, no I/O.
"""

import pytest

from src.domain.entities import (
    INSUFFICIENT_DATA,
    AuditResult,
    RiskEvaluationResult,
    derive_behavioral_floor,
    parse_behavioral_assessment,
    reconcile_behavioral_assessment,
)
from src.infra.database.database import QUAL_ASSESSMENT_TO_VERDICT

parse_cro = RiskEvaluationResult.from_cro_report


class TestCroDecisionParsing:
    """The CRO agent emits markdown, so the parser must see through it."""

    def test_parses_plain_labels(self):
        result = parse_cro("DECISION: REJECTED\nRISK TIER: EXTREME\nEXECUTIVE RATIONALE: Bad.")
        assert result.decision == "REJECTED"
        assert result.risk_tier == "EXTREME"

    def test_parses_markdown_bold_labels(self):
        """Llama 3.1 wraps labels as '**DECISION:**' in practice."""
        result = parse_cro("**DECISION:** APPROVED\n**RISK TIER:** LOW\n")
        assert result.decision == "APPROVED"
        assert result.risk_tier == "LOW"

    def test_parses_multiword_decision(self):
        result = parse_cro("DECISION: MANUAL REVIEW REQUIRED\nRISK TIER: HIGH")
        assert result.decision == "MANUAL REVIEW REQUIRED"

    def test_is_case_insensitive(self):
        result = parse_cro("decision: rejected\nrisk tier: high")
        assert result.decision == "REJECTED"
        assert result.risk_tier == "HIGH"

    def test_parses_value_on_the_next_line(self):
        """Observed live: the model puts the label on one line and the value below it."""
        result = parse_cro("**DECISION:**\n- REJECTED\n**RISK TIER:**\n- EXTREME")
        assert result.decision == "REJECTED"
        assert result.risk_tier == "EXTREME"

    def test_parses_multiword_decision_on_the_next_line(self):
        result = parse_cro("DECISION:\nMANUAL REVIEW REQUIRED\nRISK TIER: HIGH")
        assert result.decision == "MANUAL REVIEW REQUIRED"

    def test_prose_after_the_label_does_not_confuse_the_parser(self):
        report = (
            "**DECISION:** REJECTED\n**RISK TIER:** EXTREME\n"
            "**EXECUTIVE RATIONALE:**\n\nThe decision to reject rests on three triggers."
        )
        assert parse_cro(report).decision == "REJECTED"

    def test_rationale_retains_full_report(self):
        report = "DECISION: REJECTED\nRISK TIER: HIGH\nEXECUTIVE RATIONALE: Three triggers."
        assert "Three triggers." in parse_cro(report).rationale


class TestCroFailsClosed:
    """An unreadable report must never become an approval."""

    def test_unparseable_report_goes_to_manual_review(self):
        result = parse_cro("The model rambled and never emitted the required format.")
        assert result.decision == "MANUAL REVIEW REQUIRED"
        assert result.risk_tier == "HIGH"

    def test_empty_report_goes_to_manual_review(self):
        assert parse_cro("").decision == "MANUAL REVIEW REQUIRED"

    def test_none_report_goes_to_manual_review(self):
        assert parse_cro(None).decision == "MANUAL REVIEW REQUIRED"

    def test_missing_tier_alone_falls_back(self):
        result = parse_cro("DECISION: APPROVED\n")
        assert result.decision == "APPROVED"
        assert result.risk_tier == "HIGH"


class TestPolicyOutranksModel:
    """Deterministic policy wins when the LLM contradicts it."""

    def test_approval_of_critical_risk_is_escalated(self):
        result = parse_cro("DECISION: APPROVED\nRISK TIER: LOW", quant_standing="CRITICAL RISK")
        assert result.decision == "MANUAL REVIEW REQUIRED"

    def test_escalation_also_floors_the_tier(self):
        """The tier came from the same contradicted report, so it is not trusted."""
        result = parse_cro("DECISION: APPROVED\nRISK TIER: LOW", quant_standing="CRITICAL RISK")
        assert result.risk_tier == "HIGH"

    def test_escalation_does_not_lower_a_worse_tier(self):
        result = parse_cro("DECISION: APPROVED\nRISK TIER: EXTREME", quant_standing="CRITICAL RISK")
        assert result.risk_tier == "EXTREME"

    def test_rejection_of_critical_risk_is_left_alone(self):
        result = parse_cro("DECISION: REJECTED\nRISK TIER: EXTREME", quant_standing="CRITICAL RISK")
        assert result.decision == "REJECTED"

    def test_approval_of_low_risk_is_left_alone(self):
        result = parse_cro("DECISION: APPROVED\nRISK TIER: LOW", quant_standing="LOW RISK")
        assert result.decision == "APPROVED"


class TestBehavioralAssessmentParsing:
    @pytest.mark.parametrize(
        ("report", "expected"),
        [
            ("BEHAVIORAL RISK ASSESSMENT: HIGH", "HIGH"),
            ("**BEHAVIORAL RISK ASSESSMENT:** LOW", "LOW"),
            ("behavioral risk assessment: medium", "MEDIUM"),
        ],
    )
    def test_parses_each_assessment(self, report, expected):
        assert parse_behavioral_assessment(report) == expected

    def test_parses_bulleted_value_on_the_next_line(self):
        """Regression: this exact shape silently downgraded a real HIGH to MEDIUM."""
        report = (
            "**BEHAVIORAL RISK ASSESSMENT:**\n"
            "- HIGH (due to 2 delinquencies in the last 2 years)"
        )
        assert parse_behavioral_assessment(report) == "HIGH"

    def test_parses_value_after_a_blank_line(self):
        assert parse_behavioral_assessment("**BEHAVIORAL RISK ASSESSMENT:**\n\n- LOW") == "LOW"

    def test_unparseable_falls_back_to_medium(self):
        """Fail closed: an unreadable behavioural report is not treated as clean."""
        assert parse_behavioral_assessment("no label present") == "MEDIUM"

    def test_empty_falls_back_to_medium(self):
        assert parse_behavioral_assessment("") == "MEDIUM"


class TestAuditResultDefaults:
    """Defaults must be the conservative values, not optimistic ones."""

    def test_defaults_are_fail_closed(self):
        result = AuditResult(
            customer_id=1,
            risk_score=0.9,
            quant_standing="CRITICAL RISK",
            quant_report="",
            qual_report="",
            cro_report="",
        )
        assert result.decision == "MANUAL REVIEW REQUIRED"
        assert result.risk_tier == "HIGH"
        assert result.qual_assessment == "MEDIUM"

    def test_to_dict_exposes_structured_verdict(self):
        result = AuditResult(
            customer_id=101,
            risk_score=0.84,
            quant_standing="CRITICAL RISK",
            quant_report="q",
            qual_report="ql",
            cro_report="c",
            decision="REJECTED",
            risk_tier="EXTREME",
            qual_assessment="HIGH",
        )
        payload = result.to_dict()
        assert payload["decision"] == "REJECTED"
        assert payload["risk_tier"] == "EXTREME"
        assert payload["qual_assessment"] == "HIGH"


class TestBehavioralFloor:
    """The tier is computable from the record, so the model must not be trusted with it.

    Regression cover for a live case: customer 114 (0 delinquencies, 1 year employment)
    was classified LOW by the LLM, which mapped to an APPROVE vote, even though the
    prompt's own thresholds place employment under 2 years at MEDIUM.
    """

    @pytest.mark.parametrize(
        ("delinquencies", "employment_years", "expected"),
        [
            (0, 5, "LOW"),
            (0, 2, "LOW"),  # boundary: exactly 2 years is not a red flag
            (0, 1, "MEDIUM"),  # the customer 114 case
            (0, 0, "MEDIUM"),
            (1, 5, "MEDIUM"),
            (1, 1, "HIGH"),  # delinquency compounded by short tenure
            (2, 10, "HIGH"),
            (5, 10, "HIGH"),
        ],
    )
    def test_derives_tier_from_record(self, delinquencies, employment_years, expected):
        assert derive_behavioral_floor(delinquencies, employment_years) == expected

    @pytest.mark.parametrize(
        ("delinquencies", "employment_years"),
        [(None, 5), (0, None), (None, None), ("", 5), ("many", 5), (-1, 5), (0, -3)],
    )
    def test_unverifiable_record_abstains(self, delinquencies, employment_years):
        """A record that cannot be read must never resolve to LOW."""
        assert derive_behavioral_floor(delinquencies, employment_years) == INSUFFICIENT_DATA


class TestBehavioralReconciliation:
    """The model may escalate on what it read in the notes; it may never de-escalate."""

    def test_model_cannot_undercut_the_floor(self):
        assert reconcile_behavioral_assessment("LOW", "MEDIUM") == "MEDIUM"
        assert reconcile_behavioral_assessment("LOW", "HIGH") == "HIGH"
        assert reconcile_behavioral_assessment("MEDIUM", "HIGH") == "HIGH"

    def test_model_may_escalate_above_the_floor(self):
        """Only the model reads the notes, so a note-driven escalation must survive."""
        assert reconcile_behavioral_assessment("HIGH", "LOW") == "HIGH"
        assert reconcile_behavioral_assessment("MEDIUM", "LOW") == "MEDIUM"

    def test_agreement_is_preserved(self):
        assert reconcile_behavioral_assessment("LOW", "LOW") == "LOW"
        assert reconcile_behavioral_assessment("HIGH", "HIGH") == "HIGH"

    def test_unreadable_model_output_falls_back_without_undercutting(self):
        assert reconcile_behavioral_assessment("GARBAGE", "HIGH") == "HIGH"
        assert reconcile_behavioral_assessment("GARBAGE", "LOW") == "GARBAGE"

    def test_insufficient_data_outranks_a_low_reading(self):
        assert reconcile_behavioral_assessment("LOW", INSUFFICIENT_DATA) == INSUFFICIENT_DATA

    def test_high_reading_outranks_insufficient_data(self):
        assert reconcile_behavioral_assessment("HIGH", INSUFFICIENT_DATA) == "HIGH"


class TestInsufficientDataNeverApproves:
    """The whole point of the abstention: it must not reach the committee as APPROVE."""

    def test_verdict_mapping_routes_abstention_to_alert(self):
        assert QUAL_ASSESSMENT_TO_VERDICT[INSUFFICIENT_DATA] == "ALERT"
        assert QUAL_ASSESSMENT_TO_VERDICT["LOW"] == "APPROVE"

    def test_parser_recognises_the_abstention(self):
        report = "**BEHAVIORAL RISK ASSESSMENT:** INSUFFICIENT DATA"
        assert parse_behavioral_assessment(report) == INSUFFICIENT_DATA
