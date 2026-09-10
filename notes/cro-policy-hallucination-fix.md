## CRO Agent: Fabricated Policy Citations

### Bug

The CRO Decision Agent's `EXECUTIVE RATIONALE` cited committee policies that did not apply to the case at hand, in both directions:

| Case | Quant / Qual reports said | CRO output |
| --- | --- | --- |
| Customer 102 (DTI 15%, credit 820, XGBoost 0.75%) | APPROVE / SAFE, APPROVE / LOW | `REJECTED` - "hard policy violation under Policy 1" |
| Customer 136 (employment 0 yrs, otherwise clean) | APPROVE / SAFE, APPROVE / LOW | `APPROVED` - "Policy 3 (Insufficient Data)", though qualitative risk was LOW, not INSUFFICIENT DATA |
| Customer 104 (clean profile, no missing fields) | APPROVE / SAFE, APPROVE / LOW | `APPROVED` - "Policy 3 (Insufficient Data)" |

Root cause: the CRO prompt required a policy citation in every rationale but never told the model it is valid - expected, even - to cite none when nothing fires. Left to infer which policy applied from free text, `llama3.1:8b` (Q4_K_M) reached for a plausible-sounding one rather than saying so. Confirmed unrelated to `num_ctx`/`repeat_penalty` tuning: the same hallucination reproduced with both the old and new `ChatOllama` settings on identical inputs.

A second, narrower defect: `RiskEvaluationResult.from_cro_report()` only guarded one direction (an `APPROVED` verdict against a `CRITICAL RISK` quant standing was escalated to `MANUAL REVIEW REQUIRED`). A `REJECTED` verdict against a known-safe standing had no equivalent guard and passed straight through.

### Fix

Same technique already used for `describe_xgb_band()` / `describe_credit_bracket()`: resolve the judgment call in Python and hand the CRO a finished, authoritative fact instead of asking it to infer one.

* `src/domain/policy.py::determine_triggered_policy(quant_standing, qual_assessment)` - deterministically returns which policy (1, 2, 3, or none) applies.
* `src/infra/agents/agents.py::run_audit_committee()` - now floors the qualitative assessment (previously only computed *after* the CRO ran) before the CRO call, and passes the result into the prompt as `POLICY DETERMINATION, PRE-COMPUTED - AUTHORITATIVE`. The CRO's override directives and rationale rules point at this field instead of asking the model to spot violations itself.
* `src/domain/entities.py::RiskEvaluationResult.from_cro_report()` - added the symmetric guard: `REJECTED` against a non-`CRITICAL RISK` standing now also escalates to `MANUAL REVIEW REQUIRED`. `explain()` now records which direction was overruled (`overruled_decision`) instead of always narrating the approval-of-critical case.

### Verification

Regression tests in `tests/test_policy.py::TestDetermineTriggeredPolicy` and `tests/test_entities.py::TestPolicyOutranksModel`. Live re-run against Ollama for customer 136's exact reports now returns:

```text
DECISION: APPROVED
RISK TIER: LOW
EXECUTIVE RATIONALE: ... No policy was triggered, and the XGBoost Risk Score indicates a LOW probability of default.
```

### Related `ChatOllama` tuning (same session, not the fix above)

`src/infra/agents/agents.py`'s shared `llm` instance gained two explicit parameters while investigating this bug:

| Parameter | Before | After | Why |
| --- | --- | --- | --- |
| `num_ctx` | 2048 (Ollama default) | `8192` | Headroom against silent front-truncation on longer prompts (policy block + both committee reports). Measured at ~1,000 tokens for the cases here, so not the cause of this bug, but cheap insurance as notes/reports grow. |
| `repeat_penalty` | unset | `1.1` | Explicit no-op: `1.1` is Ollama's own built-in default. Made explicit for clarity; verified to change nothing. |
| `temperature` | `0.0` | `0.0` (unchanged) | Already deterministic before this session. |

An A/B run (old vs. new settings, identical CRO prompt) reproduced the exact same "Policy 3 (Insufficient Data)" hallucination under both, which is what ruled these settings out as the cause and pointed at the prompt/architecture fix above instead.
