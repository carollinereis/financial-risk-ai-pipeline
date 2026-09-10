"""Unit tests for the underwriting policy thresholds.

These are pure-logic tests: no database, no LLM, no I/O.
"""

import pytest

from src.domain.policy import (
    UnderwritingPolicy,
    determine_triggered_policy,
    explain_quantitative_standing,
    scan_note_triggers,
)

evaluate = UnderwritingPolicy.evaluate_quantitative_standing


class TestPolicyConstants:
    """Pin the thresholds so a change to them is a deliberate, visible edit."""

    def test_min_credit_score(self):
        assert UnderwritingPolicy.MIN_CREDIT_SCORE == 620

    def test_max_dti(self):
        assert UnderwritingPolicy.MAX_DTI == 0.40

    def test_xgb_high_risk_threshold(self):
        assert UnderwritingPolicy.XGB_HIGH_RISK_THRESHOLD == 0.50


class TestCriticalRiskTriggers:
    """Any one of the three triggers is sufficient for CRITICAL RISK."""

    def test_low_credit_score_alone_is_critical(self):
        assert evaluate(credit_score=619, dti=0.10, xgb_score=0.01) == "CRITICAL RISK"

    def test_high_dti_alone_is_critical(self):
        assert evaluate(credit_score=800, dti=0.41, xgb_score=0.01) == "CRITICAL RISK"

    def test_high_xgb_score_alone_is_critical(self):
        assert evaluate(credit_score=800, dti=0.10, xgb_score=0.51) == "CRITICAL RISK"

    def test_all_three_triggers_together_is_critical(self):
        assert evaluate(credit_score=500, dti=0.90, xgb_score=0.99) == "CRITICAL RISK"


class TestThresholdBoundaries:
    """The comparisons are strict (`<` and `>`), so the threshold value itself passes."""

    def test_credit_score_exactly_at_minimum_is_not_critical(self):
        # `credit_score < MIN_CREDIT_SCORE`, so 620 itself is acceptable.
        assert evaluate(credit_score=620, dti=0.10, xgb_score=0.01) == "LOW RISK"

    def test_credit_score_one_below_minimum_is_critical(self):
        assert evaluate(credit_score=619, dti=0.10, xgb_score=0.01) == "CRITICAL RISK"

    def test_dti_exactly_at_maximum_is_not_critical(self):
        # `dti > MAX_DTI`, so 0.40 itself is acceptable.
        assert evaluate(credit_score=800, dti=0.40, xgb_score=0.01) == "LOW RISK"

    def test_dti_just_above_maximum_is_critical(self):
        assert evaluate(credit_score=800, dti=0.41, xgb_score=0.01) == "CRITICAL RISK"

    def test_xgb_score_exactly_at_high_risk_threshold_is_only_moderate(self):
        # Worth knowing: `xgb_score > XGB_HIGH_RISK_THRESHOLD` is strict, so a
        # score of exactly 0.50 falls through to the MODERATE branch rather
        # than being flagged CRITICAL.
        assert evaluate(credit_score=800, dti=0.10, xgb_score=0.50) == "MODERATE RISK"

    def test_xgb_score_just_above_high_risk_threshold_is_critical(self):
        assert evaluate(credit_score=800, dti=0.10, xgb_score=0.51) == "CRITICAL RISK"


class TestModerateAndLowRisk:
    """With no CRITICAL trigger, the 0.20 xgb boundary splits MODERATE from LOW."""

    def test_xgb_score_exactly_at_moderate_boundary_is_low(self):
        assert evaluate(credit_score=800, dti=0.10, xgb_score=0.20) == "LOW RISK"

    def test_xgb_score_just_above_moderate_boundary_is_moderate(self):
        assert evaluate(credit_score=800, dti=0.10, xgb_score=0.21) == "MODERATE RISK"

    def test_pristine_profile_is_low_risk(self):
        assert evaluate(credit_score=820, dti=0.05, xgb_score=0.0) == "LOW RISK"


@pytest.mark.parametrize(
    ("credit_score", "dti", "xgb_score", "expected"),
    [
        (619, 0.30, 0.10, "CRITICAL RISK"),
        (620, 0.30, 0.10, "LOW RISK"),
        (700, 0.40, 0.10, "LOW RISK"),
        (700, 0.41, 0.10, "CRITICAL RISK"),
        (700, 0.30, 0.20, "LOW RISK"),
        (700, 0.30, 0.21, "MODERATE RISK"),
        (700, 0.30, 0.50, "MODERATE RISK"),
        (700, 0.30, 0.51, "CRITICAL RISK"),
    ],
)
def test_evaluate_quantitative_standing_table(credit_score, dti, xgb_score, expected):
    """Table-driven sweep across every branch and boundary."""
    assert evaluate(credit_score=credit_score, dti=dti, xgb_score=xgb_score) == expected


class TestExplainQuantitativeStanding:
    """The stored basis must name the deciding threshold, never imply the wrong one.

    CRITICAL RISK is a three-way OR, so a line naming a single input misattributes
    the verdict whenever a different input was the breach.
    """

    def test_low_xgb_with_failing_credit_score_does_not_blame_the_score(self):
        # The regression this exists for: 4.23% cleared its threshold by a wide
        # margin, yet the old line read "XGBoost 4.23% -> CRITICAL RISK".
        basis = explain_quantitative_standing(credit_score=587, dti=0.30, xgb_score=0.0423)
        assert "CRITICAL RISK" in basis
        assert "credit score 587 < 620" in basis
        assert "4.23% within the 50% threshold" in basis

    def test_dti_breach_is_named(self):
        basis = explain_quantitative_standing(credit_score=700, dti=0.46, xgb_score=0.0423)
        assert "DTI 46% > 40%" in basis
        assert basis.startswith("Breach: DTI 46% > 40% -> CRITICAL RISK.")

    def test_xgb_breach_is_named_as_the_breach(self):
        basis = explain_quantitative_standing(credit_score=700, dti=0.30, xgb_score=0.62)
        assert "XGBoost default probability 62.00% > 50%" in basis
        assert "Cleared: credit score 700" in basis

    def test_every_breach_is_listed_not_just_the_first(self):
        basis = explain_quantitative_standing(credit_score=590, dti=0.55, xgb_score=0.71)
        assert "credit score 590 < 620" in basis
        assert "DTI 55% > 40%" in basis
        assert "71.00% > 50%" in basis
        assert "Cleared:" not in basis

    def test_cleared_metrics_are_named_alongside_the_breach(self):
        basis = explain_quantitative_standing(credit_score=590, dti=0.10, xgb_score=0.05)
        assert "Cleared: DTI 10% within the 40% ceiling" in basis
        assert "5.00% within the 50% threshold" in basis

    def test_moderate_cites_the_moderate_threshold_not_the_hard_one(self):
        basis = explain_quantitative_standing(credit_score=800, dti=0.10, xgb_score=0.35)
        assert "MODERATE RISK" in basis
        assert "35.00% > 20%" in basis
        assert "No hard threshold breached" in basis

    def test_low_risk_reports_all_three_as_cleared(self):
        basis = explain_quantitative_standing(credit_score=820, dti=0.05, xgb_score=0.02)
        assert basis.endswith("-> LOW RISK.")
        assert "credit score 820 meets the 620 minimum" in basis
        assert "DTI 5% within the 40% ceiling" in basis
        assert "2.00% within the 50% threshold" in basis


@pytest.mark.parametrize(
    ("credit_score", "dti", "xgb_score", "expected"),
    [
        (619, 0.30, 0.10, "CRITICAL RISK"),
        (620, 0.30, 0.10, "LOW RISK"),
        (700, 0.40, 0.10, "LOW RISK"),
        (700, 0.41, 0.10, "CRITICAL RISK"),
        (700, 0.30, 0.20, "LOW RISK"),
        (700, 0.30, 0.21, "MODERATE RISK"),
        (700, 0.30, 0.50, "MODERATE RISK"),
        (700, 0.30, 0.51, "CRITICAL RISK"),
    ],
)
def test_explanation_agrees_with_the_verdict_it_explains(credit_score, dti, xgb_score, expected):
    """The basis and the evaluator must never disagree; the basis is the audit record."""
    basis = explain_quantitative_standing(credit_score=credit_score, dti=dti, xgb_score=xgb_score)
    assert f"-> {expected}." in basis
    assert evaluate(credit_score=credit_score, dti=dti, xgb_score=xgb_score) == expected


class TestNoteTriggerScan:
    """The note scan replaces an LLM read that missed its own trigger list."""

    @pytest.mark.parametrize(
        ("notes", "expected"),
        [
            ("Recent score drop due to high revolving credit usage.",
             ["credit score deterioration", "high credit utilisation"]),
            ("Revolving credit usage is high, near the account limit.",
             ["high credit utilisation"]),
            ("Cards are maxed out.", ["high credit utilisation"]),
            ("Customer has 3 late payment(s) recorded in the last 24 months.",
             ["payment delinquency in notes"]),
            ("Applicant was laid off in March; currently unemployed.",
             ["income disruption"]),
        ],
    )
    def test_triggers_are_detected(self, notes, expected):
        assert sorted(scan_note_triggers(notes)) == sorted(expected)

    @pytest.mark.parametrize(
        "notes",
        [
            # Over-redaction guard: a trigger word reporting an ABSENCE is not a flag.
            "No missed payments on record; score has improved steadily.",
            "Zero late payments in 5 years.",
            "Applicant has excellent payment history and low credit usage.",
            "Credit utilisation is low and well managed.",
            # 'high' here describes the score, not the utilisation.
            "Score is high and utilisation remains minimal.",
            "High income relative to peers in the same role.",
            "Stable employment; job satisfaction is high.",
            "Strong income stability and low financial leverage.",
            "Applicant requested a higher limit for a home renovation.",
        ],
    )
    def test_benign_text_is_not_flagged(self, notes):
        assert scan_note_triggers(notes) == []

    def test_missing_notes_are_not_flagged(self):
        assert scan_note_triggers(None) == []
        assert scan_note_triggers("") == []


class TestDetermineTriggeredPolicy:
    """The CRO is handed this verbatim so it cannot invent which policy fired.

    Regression coverage for a real hallucination: the CRO cited "Policy 3
    (Insufficient Data)" to justify an APPROVED decision on clean profiles
    where the qualitative assessment was LOW, not INSUFFICIENT DATA, and no
    policy applied at all.
    """

    def test_critical_quant_standing_triggers_policy_1(self):
        result = determine_triggered_policy("CRITICAL RISK", "LOW")
        assert "Policy 1" in result
        assert "REJECTED" in result

    def test_policy_1_outranks_qualitative_findings(self):
        """Policy 1 is checked first regardless of the qualitative reading."""
        result = determine_triggered_policy("CRITICAL RISK", "HIGH")
        assert "Policy 1" in result
        assert "Policy 2" not in result

    def test_insufficient_data_triggers_policy_3(self):
        result = determine_triggered_policy("LOW RISK", "INSUFFICIENT DATA")
        assert "Policy 3" in result
        assert "MUST NOT be APPROVED" in result

    def test_high_qualitative_risk_triggers_policy_2(self):
        result = determine_triggered_policy("MODERATE RISK", "HIGH")
        assert "Policy 2" in result

    @pytest.mark.parametrize(
        ("quant_standing", "qual_assessment"),
        [
            ("LOW RISK", "LOW"),
            ("MODERATE RISK", "LOW"),
            ("MODERATE RISK", "MEDIUM"),
        ],
    )
    def test_clean_profile_triggers_no_policy(self, quant_standing, qual_assessment):
        result = determine_triggered_policy(quant_standing, qual_assessment)
        assert "NO POLICY IS TRIGGERED" in result
        assert "TRIGGERED: " not in result  # no "Policy N is TRIGGERED:" clause present
