import re
from dataclasses import dataclass
from typing import Any


@dataclass
class CustomerProfile:
    customer_id: int
    name: str
    credit_score: int
    dti: float
    income: float
    loan_amount: float
    delinquencies: int
    cpf: str | None = None
    email: str | None = None
    phone_number: str | None = None
    employment_length_years: int | None = None
    is_high_risk: bool | None = False
    notes: str | None = None

    @classmethod
    def from_db_record(cls, record: dict, notes: str | None = None) -> "CustomerProfile":
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

# INSUFFICIENT DATA is a distinct outcome from LOW: LOW asserts a clean history was
# verified, whereas INSUFFICIENT DATA says nothing could be verified either way. A
# thin file is uncertainty, not safety, so it must never read as a vote to approve.
INSUFFICIENT_DATA = "INSUFFICIENT DATA"
BEHAVIORAL_ASSESSMENTS = ("LOW", "MEDIUM", "HIGH", INSUFFICIENT_DATA)
# Fail closed: an unreadable behavioural report is treated as elevated, not clean.
FALLBACK_BEHAVIORAL_ASSESSMENT = "MEDIUM"

# Severity ranking used to reconcile the model against deterministic policy.
# INSUFFICIENT DATA sits alongside MEDIUM: both route to human attention.
BEHAVIORAL_SEVERITY = {"LOW": 0, INSUFFICIENT_DATA: 1, "MEDIUM": 1, "HIGH": 2}


def extract_labelled_value(label: str, text: str, allowed: tuple[str, ...]) -> str | None:
    """Pulls one labelled field, tolerating the markdown the LLM adds around it."""
    # Llama wraps labels as '**DECISION:**', so asterisks may sit either side of
    # the colon; the value itself may also arrive emphasised.
    # The value may sit on the label's line, or on the next line as a list item:
    #   '**BEHAVIORAL RISK ASSESSMENT:**\n- HIGH (due to 2 delinquencies)'
    # so allow one line break plus an optional bullet before the value.
    match = re.search(
        rf"\**\s*{label}\s*\**\s*:\s*\**[ \t]*(?:\r?\n\s*[-*\u2022]?[ \t]*)?\**\s*"
        r"([A-Za-z][A-Za-z ]*)",
        text or "",
        re.IGNORECASE,
    )
    if not match:
        return None

    candidate = " ".join(match.group(1).split()).upper()
    # Longest-first so 'MANUAL REVIEW REQUIRED' wins over a bare prefix match.
    for option in sorted(allowed, key=len, reverse=True):
        if candidate.startswith(option):
            return option
    return None


def _years(count: int) -> str:
    return f"{count} year" if count == 1 else f"{count} years"


def assess_behavioral_floor(
    delinquencies: int | None, employment_length_years: int | None
) -> tuple[str, str]:
    """Computes the behavioural tier from the structured record, with its reason.

    These thresholds are stated in the qualitative agent's prompt as deterministic,
    but an LLM asked to compare integers can and does get them wrong. The record is
    already structured, so the tier is computed here and used as a floor the model
    cannot undercut.

    The reason travels with the tier so a verdict that contradicts the agent's own
    prose can say which threshold produced it, rather than appearing unexplained.
    """
    try:
        delinquency_count = int(delinquencies)
        employment_years = int(employment_length_years)
    except (TypeError, ValueError):
        # Nothing verifiable in the record: abstain rather than assume a clean file.
        return INSUFFICIENT_DATA, "delinquency count or employment length not recorded"

    if delinquency_count < 0 or employment_years < 0:
        return INSUFFICIENT_DATA, "record holds a negative delinquency count or employment length"

    if delinquency_count >= 2:
        return "HIGH", f"{delinquency_count} delinquencies in the last 2 years"
    if delinquency_count == 1 and employment_years < 2:
        return "HIGH", (
            f"1 delinquency combined with {_years(employment_years)} of employment, "
            "under the 2-year threshold"
        )
    if delinquency_count == 1:
        return "MEDIUM", "1 delinquency in the last 2 years"
    if employment_years < 2:
        return "MEDIUM", (
            f"{_years(employment_years)} of employment, under the 2-year threshold"
        )
    return "LOW", f"zero delinquencies and {_years(employment_years)} of employment"


def derive_behavioral_floor(
    delinquencies: int | None, employment_length_years: int | None
) -> str:
    """Returns only the tier the structured record establishes."""
    return assess_behavioral_floor(delinquencies, employment_length_years)[0]


def explain_behavioral_verdict(
    model_assessment: str, floor: str, floor_reason: str, final: str
) -> str:
    """States how the stored qualitative verdict was reached.

    The committee's prose is the model's unmodified reading, so when policy floors
    it the report and the recorded vote disagree on their face. This sentence is
    what makes that disagreement legible instead of looking like a defect.
    """
    if final != model_assessment:
        return (
            f"Agent assessed {model_assessment}; policy floor raised it to {final} "
            f"({floor_reason})."
        )
    if model_assessment != floor:
        return (
            f"Agent assessed {model_assessment}, above the record's {floor} floor "
            f"({floor_reason})."
        )
    return f"Agent assessed {model_assessment}; record concurs ({floor_reason})."


def reconcile_behavioral_assessment(model_assessment: str, floor: str) -> str:
    """Takes whichever of the model's reading and the policy floor is more severe.

    The model may escalate, because it alone reads the free-text notes and can find
    signals no threshold captures. It may never de-escalate below what the structured
    record establishes.
    """
    model_rank = BEHAVIORAL_SEVERITY.get(model_assessment, BEHAVIORAL_SEVERITY[FALLBACK_BEHAVIORAL_ASSESSMENT])
    floor_rank = BEHAVIORAL_SEVERITY.get(floor, BEHAVIORAL_SEVERITY[INSUFFICIENT_DATA])
    # Ties keep the floor, so the record's explanation of *why* survives.
    return model_assessment if model_rank > floor_rank else floor


def parse_behavioral_assessment(qual_report: str) -> str:
    """Reads the qualitative agent's BEHAVIORAL RISK ASSESSMENT line."""
    return (
        extract_labelled_value("BEHAVIORAL RISK ASSESSMENT", qual_report, BEHAVIORAL_ASSESSMENTS)
        or FALLBACK_BEHAVIORAL_ASSESSMENT
    )


@dataclass
class RiskEvaluationResult:
    decision: str  # APPROVED, REJECTED, MANUAL REVIEW REQUIRED
    risk_tier: str  # LOW, MEDIUM, HIGH, EXTREME
    rationale: str
    # True when deterministic policy overruled the CRO's own decision. Recorded so
    # a verdict that contradicts the report can say so instead of looking wrong.
    policy_escalated: bool = False

    VALID_DECISIONS = ("APPROVED", "REJECTED", "MANUAL REVIEW REQUIRED")
    VALID_TIERS = ("LOW", "MEDIUM", "HIGH", "EXTREME")

    # Fail-closed defaults: an unreadable committee report must never become an
    # approval, so it lands in the human queue at a conservative tier instead.
    FALLBACK_DECISION = "MANUAL REVIEW REQUIRED"
    FALLBACK_TIER = "HIGH"

    @classmethod
    def from_cro_report(cls, report: str, quant_standing: str | None = None) -> "RiskEvaluationResult":
        """Parses the CRO agent's prose into a structured, machine-actionable decision."""
        text = report or ""

        decision = extract_labelled_value("DECISION", text, cls.VALID_DECISIONS) or cls.FALLBACK_DECISION
        risk_tier = extract_labelled_value("RISK TIER", text, cls.VALID_TIERS) or cls.FALLBACK_TIER

        # Deterministic policy outranks the LLM. Hard policy 1 in the CRO prompt
        # forbids approving a CRITICAL RISK profile, so if the model does it
        # anyway the case is escalated rather than trusted.
        policy_escalated = False
        if quant_standing == "CRITICAL RISK" and decision == "APPROVED":
            decision = cls.FALLBACK_DECISION
            # The tier came from the same contradicted report, so it is not
            # trustworthy either; floor it at the conservative default.
            risk_tier = max(risk_tier, cls.FALLBACK_TIER, key=cls.VALID_TIERS.index)
            policy_escalated = True

        return cls(
            decision=decision,
            risk_tier=risk_tier,
            rationale=text.strip(),
            policy_escalated=policy_escalated,
        )

    def explain(self) -> str:
        """States how the stored committee decision was reached."""
        if self.policy_escalated:
            return (
                "CRO approved a CRITICAL RISK profile; policy escalated it to "
                f"{self.decision} at {self.risk_tier} tier."
            )
        return f"CRO decided {self.decision} at {self.risk_tier} risk tier."



@dataclass
class AuditResult:
    """Represents the complete output of the multi-agent risk audit committee."""
    customer_id: int
    risk_score: float
    quant_standing: str
    quant_report: str
    qual_report: str
    cro_report: str
    decision: str = "MANUAL REVIEW REQUIRED"
    risk_tier: str = "HIGH"
    qual_assessment: str = FALLBACK_BEHAVIORAL_ASSESSMENT

    def to_dict(self) -> dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "risk_score": self.risk_score,
            "quant_standing": self.quant_standing,
            "quant_report": self.quant_report,
            "qual_report": self.qual_report,
            "cro_report": self.cro_report,
            "decision": self.decision,
            "risk_tier": self.risk_tier,
            "qual_assessment": self.qual_assessment,
        }
