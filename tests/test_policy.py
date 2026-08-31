"""Unit tests for the underwriting policy thresholds.

These are pure-logic tests: no database, no LLM, no I/O.
"""

import pytest

from src.domain.policy import UnderwritingPolicy

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
