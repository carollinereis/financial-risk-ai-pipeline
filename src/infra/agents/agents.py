import time
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

import src.infra.config  # noqa: F401 - import triggers load_dotenv() for LangSmith tracing
from src.domain.entities import (
    CustomerProfile,
    assess_behavioral_floor,
    parse_behavioral_assessment,
    reconcile_behavioral_assessment,
)
from src.domain.policy import (
    UnderwritingPolicy,
    determine_triggered_policy,
    render_policies_for_prompt,
    scan_note_triggers,
)

# Initialize local Llama 3 model via Ollama (deterministic compliance).
# The timeout is mandatory: without it a hung Ollama blocks the committee - and the API
# request behind it - indefinitely, with three sequential agent calls per audit.
LLM_TIMEOUT_SECONDS = 30.0
llm = ChatOllama(
    model="llama3.1",
    temperature=0.0,
    timeout=LLM_TIMEOUT_SECONDS,
    # Ollama's default is 2048 tokens; the CRO prompt alone (policy block + both
    # committee reports) can approach that, and a truncated prompt silently drops
    # context from the front rather than erroring. Headroom, not a fix for a
    # measured overflow.
    num_ctx=8192,
    # Guards against the local model degenerating into repeated phrases on long
    # structured outputs; does not affect determinism at temperature=0.0.
    repeat_penalty=1.1,
)

# Band boundary above the hard-risk threshold; scores past it are unambiguously severe.
XGB_SEVERE_THRESHOLD = 0.75


def describe_xgb_band(xgb_score: float) -> str:
    """Resolves the XGBoost score into its policy band deterministically, so
    agents repeat a fixed sentence instead of comparing the number themselves."""
    threshold = UnderwritingPolicy.XGB_HIGH_RISK_THRESHOLD
    if xgb_score > XGB_SEVERE_THRESHOLD:
        band = "HIGH"
        reading = "a HIGH probability of default"
    elif xgb_score > threshold:
        band = "MODERATE"
        reading = "a MODERATE probability of default"
    else:
        band = "LOW"
        reading = (
            "a LOW probability of default - this is a FAVOURABLE model signal and must "
            "NEVER be described as a high probability of default, elevated risk, or "
            "likely default"
        )

    return (
        f"{xgb_score:.2%} -> band {band}: the model indicates {reading} "
        f"(hard-risk threshold is {threshold:.0%})."
    )


def describe_credit_bracket(credit_score: int) -> str:
    """Resolves a credit score into its FICO bracket deterministically, so the
    agent matches a word instead of comparing ranges itself."""
    if credit_score < 620:
        return "POOR"
    if credit_score < 670:
        return "FAIR"
    if credit_score < 740:
        return "GOOD"
    return "EXCEPTIONAL"


# ==========================================
# AGENT 1: QUANTITATIVE RISK ANALYST
# ==========================================
quant_prompt = ChatPromptTemplate.from_template("""
You are a Senior Quantitative Credit Analyst.
Evaluate the following customer metrics deterministically:

Customer Profile:
{profile_data}

Model Default Risk (XGBoost): {xgb_score}
Quantitative Policy Assessment: {quant_standing}

CRITICAL MANDATORY THRESHOLDS:
- Debt-to-income (DTI) > 0.40 is a HARD POLICY VIOLATION (MANDATORY REJECT).
- Credit score < 620 is a HARD POLICY VIOLATION (HIGH RISK).
- The XGBoost score has ALREADY been classified below. Repeat that band verbatim and do NOT
  re-derive, re-compare, or re-interpret it.

XGBoost Band (PRE-COMPUTED, AUTHORITATIVE): {xgb_band}

Instructions:
Provide a structured quantitative summary:
1. METRIC VULNERABILITIES: List each metric failing threshold (e.g., "DTI is 0.42 > 0.40"). If a metric violates a hard threshold, explicitly write "HARD POLICY VIOLATION: MANDATORY REJECT".
2. MODEL ASSESSMENT: State the XGBoost Risk Score and Quantitative Policy Assessment.
3. OVERALL QUANTITATIVE STANDING: Classify as [SAFE, MODERATE, or CRITICAL RISK].
""")

quant_agent = quant_prompt | llm


# ==========================================
# AGENT 2: QUALITATIVE AUDIT & BEHAVIOR AGENT
# ==========================================
qual_prompt = ChatPromptTemplate.from_template("""
You are a Strict Compliance & Behavioral Risk Auditor.

Behavioral Record (verified system data):
{behavioral_record}

Customer Notes:
"{customer_notes}"

SCOPE
- Use only the two sources above. Invent nothing.
- Audit delinquencies, employment tenure, the FICO bracket, and the notes.
- Never mention or evaluate DTI, loan amount, annual income, or the XGBoost score - those
  belong to the Quantitative Analyst. Ignore them even if they appear in the notes.
- The FICO bracket is given in the record. Use that word; do not re-derive it from the number.

STEP 1 - The notes have already been scanned. Pre-scanned note flags: {note_flags}
Report every pre-scanned flag on the NOTE FLAGS line - they are established findings, not
suggestions, and must not be judged, softened, or excused. Add any further flag you find in
the notes yourself: a credit score drop, credit usage called high or near-limit, missed or
late payments, collections, job loss, or financial distress. Write None only when the
pre-scanned list is None and you found nothing.

STEP 2 - Record flags: delinquencies of 1 or more (state the count); employment under 2 years
(state the tenure); a POOR or FAIR FICO bracket.

STEP 3 - Assess:
- NOTE FLAGS is not None  -> MEDIUM at minimum.
- 2 or more delinquencies, or a POOR bracket -> HIGH.
- LOW requires NOTE FLAGS of None AND no record flags.
- INSUFFICIENT DATA only when the record omits the delinquency count or employment length.

Output exactly these four lines, nothing before or after:
NOTE FLAGS: <quoted phrases from the notes, or None>
RED FLAGS: <note flags plus record flags with exact values, or None>
POSITIVE SIGNALS: <list, or None>
BEHAVIORAL RISK ASSESSMENT: <LOW, MEDIUM, HIGH, or INSUFFICIENT DATA>
""")

qual_agent = qual_prompt | llm


# ==========================================
# AGENT 3: CHIEF RISK OFFICER (CRO) DECISION AGENT
# ==========================================
cro_prompt = ChatPromptTemplate.from_template("""
You are the Chief Risk Officer (CRO) function of a commercial bank.
Apply the underwriting policies below to the Quantitative Analyst and Qualitative Auditor reports.

--- QUANTITATIVE REPORT ---
{quant_report}

--- QUALITATIVE REPORT ---
{qual_report}

--- MODEL DEFAULT RISK (XGBoost), PRE-COMPUTED - AUTHORITATIVE ---
{xgb_band}

This band was computed deterministically and is the ONLY permitted reading of the model score.
Do NOT perform any numeric comparison of your own, and do NOT accept a contradictory
characterisation of the score from the reports above - they may contain arithmetic errors.

HARD BANK UNDERWRITING POLICIES (MANDATORY):
{policy_block}

--- POLICY DETERMINATION, PRE-COMPUTED - AUTHORITATIVE ---
{policy_determination}

This determination was computed deterministically from the same structured record the reports
above are describing. It is the ONLY permitted answer to "which policy fired". Do NOT re-derive
it, do NOT accept a contradictory policy citation from the reports above, and do NOT cite a
policy number this determination does not name - inventing one is a critical compliance failure.

CRITICAL OVERRIDE DIRECTIVES (NON-NEGOTIABLE ENFORCEMENT):
1. HARD POLICY TRUMPS ML SCORES: If the PRE-COMPUTED POLICY DETERMINATION above says Policy 1 is
   TRIGGERED, the DECISION MUST BE "REJECTED".
2. ABSOLUTE PROHIBITION ON MANUAL REVIEW FOR HARD VIOLATIONS: You are STRICTLY FORBIDDEN from
   issuing "MANUAL REVIEW REQUIRED" when Policy 1 is TRIGGERED. Favorable XGBoost risk scores
   CANNOT override a hard policy violation.
3. MANUAL REVIEW CONDITIONS: Output "MANUAL REVIEW REQUIRED" ONLY when the PRE-COMPUTED POLICY
   DETERMINATION says Policy 2 or Policy 3 is TRIGGERED (or the reports raise a genuine, unresolved
   conflict Policy 1 does not settle) - never when it says NO POLICY IS TRIGGERED.
4. NO POLICY TRIGGERED MEANS APPROVE: If the PRE-COMPUTED POLICY DETERMINATION says NO POLICY IS
   TRIGGERED, DECISION MUST BE "APPROVED" and the rationale MUST NOT name Policy 1, 2, or 3 as a
   cause. State plainly that no policy was triggered instead.

RATIONALE STYLE (MANDATORY):
- Write impersonally. Do NOT use 'I', 'we', or 'my decision'.
- Cite only the policy the PRE-COMPUTED POLICY DETERMINATION names as TRIGGERED, with the exact
  values from the reports that back it (e.g., "DTI Ratio of 0.42 exceeds maximum allowed threshold
  of 0.40 under Policy 1"). If it says NO POLICY IS TRIGGERED, cite none.
- Do NOT restate or summarize the policy list.
- Report the XGBoost score only with the band given in the PRE-COMPUTED section above.
- When the DECISION is REJECTED on a hard policy violation AND that band is LOW, the rationale
  MUST state that the rejection is enforced by the hard policy threshold DESPITE the low and
  favourable ML risk score. The hard policy is then the sole stated cause; the model score must
  NOT be recruited as supporting evidence for the rejection.
- RISK TIER must be exactly one of LOW, MEDIUM, HIGH, EXTREME. No other wording is accepted.

Output ONLY the three fields below. No preamble, no closing note.

Required Output Format:
DECISION: [APPROVED, REJECTED, or MANUAL REVIEW REQUIRED]
RISK TIER: [LOW, MEDIUM, HIGH, EXTREME]
EXECUTIVE RATIONALE: [2-3 impersonal sentences citing the exact policy triggers and values that fired them]
""")

cro_agent = cro_prompt | llm


def _timed(fn, payload):
    """Invokes fn(payload) and returns (result, elapsed_ms)."""
    started = time.perf_counter()
    result = fn(payload)
    return result, int((time.perf_counter() - started) * 1000)


# ==========================================
# MULTI-AGENT ORCHESTRATION PIPELINE
# ==========================================
def run_audit_committee(
    profile: CustomerProfile,
    xgb_score: float,
    sanitized_notes: str,
    quant_standing: str
) -> dict:
    """
    Pure Multi-Agent Execution Unit.
    Receives pre-fetched domain entity and calculated features, executes
    the 3 LLM agents sequentially, and returns structured results.
    """
    # 1. Format profile text from Domain Entity (No DB calls!)
    profile_summary = (
        f"Customer ID: {profile.customer_id}\n"
        f"Name: {profile.name}\n"
        f"Credit Score: {profile.credit_score}\n"
        f"DTI Ratio: {profile.dti:.2f}\n"
        f"Annual Income: ${profile.income:,.2f}\n"
        f"Loan Requested: ${profile.loan_amount:,.2f}\n"
        f"Delinquencies (2 yrs): {profile.delinquencies}"
    )

    # 2. Agent 1: Quantitative Risk Analyst
    # Resolved once in Python so every agent narrates the same, arithmetically correct band.
    xgb_band = describe_xgb_band(xgb_score)

    quant_res, quant_ms = _timed(quant_agent.invoke, {
        "profile_data": profile_summary,
        "xgb_score": f"{xgb_score:.2%}",
        "xgb_band": xgb_band,
        "quant_standing": quant_standing
    })

    # 3. Agent 2: Qualitative Audit Specialist
    # Behavioural facts come from structured columns, never from PII fields, so the
    # auditor can flag real history instead of guessing from free text alone.
    #
    # DTI and loan amount are withheld: giving the auditor a breaching ratio invites
    # it to rationalize it as a behavioral positive instead of flagging it.
    employment = profile.employment_length_years
    behavioral_record = (
        f"- Delinquencies (last 2 years): {profile.delinquencies}\n"
        f"- Employment length: {employment if employment is not None else 'Not recorded'} years\n"
        f"- Credit Score: {profile.credit_score} "
        f"(FICO bracket: {describe_credit_bracket(profile.credit_score)})"
    )

    note_flags = scan_note_triggers(sanitized_notes)
    qual_res, qual_ms = _timed(qual_agent.invoke, {
        "behavioral_record": behavioral_record,
        "customer_notes": sanitized_notes if sanitized_notes else "No notes provided.",
        "note_flags": ", ".join(note_flags) if note_flags else "None",
    })

    # The qualitative tier is checkable against the structured record, so the model's
    # reading is floored by deterministic policy - same reasoning as xgb_band - before
    # it is used to decide which policy applies. Without this, a model reading of "LOW"
    # that undercuts a structural floor (e.g. sub-2-year employment) would let the CRO
    # miss a Policy 2/3 trigger the record actually supports.
    model_assessment = parse_behavioral_assessment(qual_res.content)
    behavioral_floor, _floor_reason = assess_behavioral_floor(
        profile.delinquencies,
        profile.employment_length_years,
        profile.credit_score,
        note_flags,
    )
    qual_assessment = reconcile_behavioral_assessment(model_assessment, behavioral_floor)

    # 4. Agent 3: Chief Risk Officer (Synthesizer)
    cro_res, cro_ms = _timed(cro_agent.invoke, {
        "quant_report": quant_res.content,
        "qual_report": qual_res.content,
        # Rendered from src.domain.policy so the agent is judged against exactly the
        # rules the dashboard shows the underwriter.
        "policy_block": render_policies_for_prompt(),
        "xgb_band": xgb_band,
        "policy_determination": determine_triggered_policy(quant_standing, qual_assessment),
    })

    return {
        "quant_analysis": quant_res.content,
        "qual_analysis": qual_res.content,
        "cro_decision": cro_res.content,
        "qual_assessment": qual_assessment,
        "timings_ms": {
            "quant": quant_ms,
            "qual": qual_ms,
            "cro": cro_ms,
        },
    }

if __name__ == "__main__":
    # Isolated smoke test: DTI 0.45 breach with a LOW XGBoost score — verifies
    # the CRO rejects on policy without recruiting the low score as evidence.
    mock_profile = CustomerProfile(
        customer_id=101,
        name="Alice Smith",
        credit_score=700,
        dti=0.45,
        income=55000.0,
        loan_amount=15000.0,
        delinquencies=0,
        employment_length_years=6,
        notes="Underwriter Note: Applicant changed jobs recently due to relocation."
    )
    mock_xgb_score = 0.0423

    print("\n==================================================")
    print("RUNNING ISOLATED MULTI-AGENT TEST")
    print("==================================================")

    results = run_audit_committee(
        profile=mock_profile,
        xgb_score=mock_xgb_score,
        sanitized_notes=mock_profile.notes,
        quant_standing=UnderwritingPolicy.evaluate_quantitative_standing(
            credit_score=mock_profile.credit_score,
            dti=mock_profile.dti,
            xgb_score=mock_xgb_score,
        ),
    )

    print("\n--- Quantitative Report ---")
    print(results["quant_analysis"])

    print("\n--- Qualitative Report ---")
    print(results["qual_analysis"])

    print("\n--- CRO Final Decision ---")
    print(results["cro_decision"])

    print("\n--- Agent Execution Timings (ms) ---")
    print(results["timings_ms"])
