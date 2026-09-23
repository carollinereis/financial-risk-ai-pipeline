"""Tests for src/infra/agents/agents.py.

Focused specifically on the CRO's quant_basis citation fix in
run_audit_committee() / cro_prompt, which previously had zero test coverage -
that gap is why the original citation-hallucination bug (Policy 1 citing DTI
when credit score was the actual trigger) shipped uncaught.
explain_quantitative_standing() itself is already thoroughly covered in
test_policy.py; nothing here duplicates that - these tests only check it is
correctly wired into the CRO prompt (Layers 1-2) and that the real model
actually uses it (Layer 3).
"""

import pytest

from src.domain.entities import CustomerProfile
from src.domain.policy import UnderwritingPolicy, explain_quantitative_standing
from src.infra.agents import agents

# Three single-trigger profiles: each breaches exactly one of the three
# CRITICAL RISK inputs (credit score, DTI, XGBoost score), so a rationale
# naming the wrong one is unambiguous.
#
# CREDIT_SCORE_ALONE deliberately pairs the breach with a DTI close to (but
# under) its own 0.40 cap rather than a clearly-safe DTI: against the unfixed
# prompt this is exactly the ambiguity that reproduced the original bug - the
# CRO fabricated "DTI Ratio of 0.38 exceeds maximum allowed threshold of
# 0.40" (0.38 does not exceed 0.40) and ignored the real credit-score breach.
# A clearly-safe DTI (e.g. 0.20) did not reproduce the bug in manual testing;
# this near-miss value does, consistently, at temperature=0.0. DTI_ALONE and
# XGB_ALONE use clearly-safe values for the other two metrics because, in the
# same manual testing, near-miss values there did not reliably discriminate
# fixed from unfixed behaviour (or, in one XGB_ALONE combination, exposed a
# separate, deeper hallucination this specific fix does not resolve - the
# model contradicted its own PRE-COMPUTED QUANTITATIVE BASIS outright).
CREDIT_SCORE_ALONE = {"credit_score": 600, "dti": 0.38, "xgb_score": 0.10}
DTI_ALONE = {"credit_score": 625, "dti": 0.55, "xgb_score": 0.05}
XGB_ALONE = {"credit_score": 750, "dti": 0.20, "xgb_score": 0.65}


def _make_profile(credit_score, dti):
    return CustomerProfile(
        customer_id=9001,
        name="Test Person",
        credit_score=credit_score,
        dti=dti,
        income=60000.0,
        loan_amount=15000.0,
        delinquencies=0,
        employment_length_years=5,
        notes="",
    )


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _RecordingAgent:
    """Stands in for a `prompt | llm` chain: records every payload it is
    invoked with and returns fixed content, so a test can assert on what an
    agent was actually called with without touching Ollama.
    """

    def __init__(self, content=""):
        self.content = content
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        return _FakeResponse(self.content)


# A syntactically valid qualitative report, so parse_behavioral_assessment()
# inside run_audit_committee reads a real LOW instead of falling back.
_QUAL_CONTENT = (
    "NOTE FLAGS: None\nRED FLAGS: None\nPOSITIVE SIGNALS: None\nBEHAVIORAL RISK ASSESSMENT: LOW"
)


class TestCroQuantBasisWiring:
    """Layer 1: the CRO agent must be invoked with the same quant_basis
    explain_quantitative_standing() would produce for the audited profile.
    Fast - the LLM is entirely mocked out, no Ollama call is made.
    """

    def _run(self, monkeypatch, credit_score, dti, xgb_score):
        cro_stub = _RecordingAgent("DECISION: REJECTED\nRISK TIER: HIGH\nEXECUTIVE RATIONALE: stub")
        monkeypatch.setattr(agents, "quant_agent", _RecordingAgent("stub quant report"))
        monkeypatch.setattr(agents, "qual_agent", _RecordingAgent(_QUAL_CONTENT))
        monkeypatch.setattr(agents, "cro_agent", cro_stub)

        profile = _make_profile(credit_score, dti)
        quant_standing = UnderwritingPolicy.evaluate_quantitative_standing(
            credit_score=credit_score, dti=dti, xgb_score=xgb_score
        )
        agents.run_audit_committee(
            profile=profile,
            xgb_score=xgb_score,
            sanitized_notes="",
            quant_standing=quant_standing,
        )

        assert len(cro_stub.calls) == 1
        return cro_stub.calls[0]

    def test_credit_score_alone_cites_credit_score_not_dti(self, monkeypatch):
        payload = self._run(monkeypatch, **CREDIT_SCORE_ALONE)
        assert payload["quant_basis"] == explain_quantitative_standing(**CREDIT_SCORE_ALONE)
        assert "credit score 600 < 620" in payload["quant_basis"]
        # DTI is close to its cap but still cleared, so it must be named cleared -
        # not phrased as a breach (the exact fabrication the original bug made).
        assert "DTI 38% within the 40% ceiling" in payload["quant_basis"]

    def test_dti_alone_cites_dti_not_credit_score(self, monkeypatch):
        payload = self._run(monkeypatch, **DTI_ALONE)
        assert payload["quant_basis"] == explain_quantitative_standing(**DTI_ALONE)
        assert "DTI 55% > 40%" in payload["quant_basis"]
        assert "credit score 625 meets the 620 minimum" in payload["quant_basis"]

    def test_xgb_alone_cites_xgboost_not_credit_score_or_dti(self, monkeypatch):
        payload = self._run(monkeypatch, **XGB_ALONE)
        assert payload["quant_basis"] == explain_quantitative_standing(**XGB_ALONE)
        assert "XGBoost default probability 65.00% > 50%" in payload["quant_basis"]
        assert "credit score 750 meets the 620 minimum" in payload["quant_basis"]
        assert "DTI 20% within the 40% ceiling" in payload["quant_basis"]


class TestCroPromptTemplate:
    """Layer 2: the prompt text itself must declare quant_basis and must no
    longer contain the old hardcoded worked example - this guards specifically
    against someone reverting the prompt wording while leaving the Python
    wiring (Layer 1) intact.
    """

    def test_prompt_declares_quant_basis_placeholder(self):
        assert "{quant_basis}" in agents.cro_prompt.messages[0].prompt.template

    def test_prompt_no_longer_has_old_hardcoded_dti_example(self):
        assert "DTI Ratio of 0.42" not in agents.cro_prompt.messages[0].prompt.template


@pytest.mark.integration
class TestCroCitationAgainstRealModel:
    """Layer 3: the real committee, run against an actual local Ollama model.

    This is a best-effort check on LLM prose, not a hard guarantee - llama3.1
    does not reliably follow instructions (see the comment above
    NOTE_TRIGGER_PATTERNS in src/domain/policy.py for another documented case
    of the same unreliability). An occasional failure here from unusual model
    phrasing is a real possibility and not necessarily a regression; a
    consistent failure across runs is the signal worth investigating.
    """

    def _run(self, credit_score, dti, xgb_score):
        profile = _make_profile(credit_score, dti)
        quant_standing = UnderwritingPolicy.evaluate_quantitative_standing(
            credit_score=credit_score, dti=dti, xgb_score=xgb_score
        )
        result = agents.run_audit_committee(
            profile=profile,
            xgb_score=xgb_score,
            sanitized_notes="",
            quant_standing=quant_standing,
        )
        return result["cro_decision"]

    def test_credit_score_alone_trigger_cites_credit_score_not_dti(self):
        decision = self._run(**CREDIT_SCORE_ALONE)
        assert "credit score" in decision.lower()
        assert "600" in decision
        assert "dti" not in decision.lower()

    def test_dti_alone_trigger_cites_dti_not_credit_score(self):
        decision = self._run(**DTI_ALONE)
        assert "dti" in decision.lower()
        assert "credit score" not in decision.lower()

    def test_xgb_alone_trigger_cites_xgboost_not_credit_score_or_dti(self):
        decision = self._run(**XGB_ALONE)
        assert "xgboost" in decision.lower()
        assert "credit score" not in decision.lower()
        assert "dti" not in decision.lower()
