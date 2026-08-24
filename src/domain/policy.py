class UnderwritingPolicy:
    """Encodes non-negotiable commercial banking risk thresholds."""

    MIN_CREDIT_SCORE = 620
    MAX_DTI = 0.40
    XGB_HIGH_RISK_THRESHOLD = 0.50

    @staticmethod
    def evaluate_quantitative_standing(credit_score: int, dti: float, xgb_score: float) -> str:
        """Determines if a profile is CRITICAL, MODERATE, or LOW risk based on policy."""
        if credit_score < UnderwritingPolicy.MIN_CREDIT_SCORE or dti > UnderwritingPolicy.MAX_DTI or xgb_score > UnderwritingPolicy.XGB_HIGH_RISK_THRESHOLD:
            return "CRITICAL RISK"
        elif xgb_score > 0.20:
            return "MODERATE RISK"
        return "LOW RISK"
