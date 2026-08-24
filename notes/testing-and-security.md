# Testing & Security

Technical reference for the automated test suite and the sanitization layer of the
Financial Risk AI Pipeline.

---

## 1. Executive Summary & Security Architecture

The pipeline routes customer credit data through a machine-learning scoring model and a
three-agent LLM committee. Two categories of untrusted data enter that flow: personally
identifiable information (PII) retrieved from DuckDB, and free-text underwriter notes that
are ultimately rendered into an LLM prompt. The sanitization layer in
`src/infra/security/security.py` governs both.

Two principles direct the design:

- **Sanitize at the boundary.** Transformation occurs where records leave the data-access
  layer, so downstream consumers — the agent committee, the FastAPI responses, and the
  Streamlit interface — receive protected values by default rather than by discipline.
- **Fail closed.** When an input does not match an expected shape, the layer returns a
  fixed placeholder instead of the original value. Unrecognized input is treated as
  sensitive.

### Control placement

```text
   DuckDB ──► agent_tools.get_customer_financial_profile ──► mask_cpf / mask_email
     │                                                                │
     │                                                                ▼
     └──────► agent_tools.get_sanitized_customer_notes ──► sanitize_input
                                                                      │
                                                                      ▼
                     RunRiskAuditUseCase.execute ──► sanitize_input ──► Agent committee
                                                                      │
                                                                      ▼
                                                        FastAPI  /  Streamlit
```

| Control | Function | Applied at |
| --- | --- | --- |
| CPF masking | `mask_cpf` | `agent_tools.get_customer_financial_profile` |
| Email masking | `mask_email` | `agent_tools.get_customer_financial_profile` |
| Phone masking | `mask_phone` | `security.get_sanitized_customer_data` |
| Prompt-injection filtering | `sanitize_input` | `agent_tools.get_sanitized_customer_notes`, `RunRiskAuditUseCase.execute` |
| Parameterized SQL | — | `security.get_sanitized_customer_data` |

Customer notes are sanitized before reaching the agent committee, so no raw underwriter
text is interpolated into an LLM prompt.

---

## 2. Test Suite Overview & Quickstart

### Dependencies

Declared under `# Dev tooling` in `requirements.txt`:

| Package | Version | Purpose |
| --- | --- | --- |
| `pytest` | `>=8.0.0` | Test runner. |
| `httpx` | `>=0.27.0` | Required by `fastapi.testclient.TestClient` for API-level tests. |

### Configuration

`pytest.ini` at the repository root:

```ini
[pytest]
testpaths = tests
pythonpath = .
addopts = -q --strict-markers
```

`pythonpath = .` places the repository root on `sys.path`. Every module uses absolute
`src.*` imports, so collection fails without it. `--strict-markers` converts an unregistered
marker into an error rather than a silent no-op.

### Execution

All commands run from the repository root.

```bash
source venv/bin/activate     # enables the bare `pytest` entry point
pip install -r requirements.txt
pytest                       # full suite
```

Without an activated environment, substitute `./venv/bin/python -m pytest`.

```bash
pytest tests/test_security.py                                   # one module
pytest tests/test_security.py::TestMaskCpf                      # one class
pytest tests/test_policy.py::TestPolicyConstants::test_max_dti  # one case
pytest -k "cpf or dti"    # select by name
pytest -v                 # list individual test names
pytest -x                 # halt on first failure
```

### Coverage

**63 tests, full suite under one second.**

| Module | Target | Tests | Scope |
| --- | --- | :---: | --- |
| `tests/test_policy.py` | `src/domain/policy.py` | 24 | Underwriting thresholds and decision-boundary logic. |
| `tests/test_security.py` | `src/infra/security/security.py` | 39 | PII masking, prompt-injection filtering, sanitized record retrieval. |

`tests/test_policy.py` pins the three policy constants — `MIN_CREDIT_SCORE = 620`,
`MAX_DTI = 0.40`, `XGB_HIGH_RISK_THRESHOLD = 0.50` — so threshold drift surfaces as a
failing assertion. It exercises each `CRITICAL RISK` trigger in isolation and in
combination, and sweeps the boundaries in a table-driven parametrization. The comparisons
in `evaluate_quantitative_standing` are strict, so a threshold value itself is acceptable:
a credit score of exactly 620, a DTI of exactly 0.40, and an XGBoost score of exactly 0.50
do not trigger `CRITICAL RISK`.

`tests/test_security.py` covers each masking function across valid, malformed, empty, and
non-string input; every active injection pattern; and `get_sanitized_customer_data`,
including an assertion that no raw PII appears anywhere in the returned record and a check
that the customer lookup remains parameterized.

### Determinism and isolation

The suite performs no network I/O and acquires no database lock, and may therefore run
while the API or Streamlit application is active.

- `get_sanitized_customer_data` is the only covered function that reaches DuckDB; its
  connection is replaced with a `MagicMock` context manager.
- The `.duckdb` file is byte-identical before and after a run, and no write-ahead log is
  produced.
- The agent layer is never imported by the modules under test, so no Ollama client is
  constructed.

### Areas for future coverage

`src/api/`, `src/application/run_risk_audit.py`, `src/infra/ml/`, `src/infra/agents/`,
`src/infra/database/`, and `app.py` are not yet covered. The API layer is the highest-value
next target: `httpx` is already declared, and `TestClient` combined with a stubbed
`RunRiskAuditUseCase` keeps such tests lock-free.

---

## 3. Implemented Security Protections

### 3.1 Multi-qualifier prompt-injection defense

`sanitize_input` normalizes free text in two stages before it reaches an LLM prompt.

Stage one removes structural characters used to smuggle markup or escape sequences:

```python
cleaned = re.sub(r"[<>{}\\]", "", text)
```

Stage two replaces known instruction-override phrasings with the sentinel
`[REDACTED_INJECTION_ATTEMPT]`. The governing pattern accepts an unbounded run of qualifier
words between the verb and its object:

```python
r"(?i)ignore\s+(?:all\s+|previous\s+|prior\s+|the\s+|above\s+)*instructions.*"
```

The `*` quantifier over a non-capturing alternation is what generalizes the rule. A single
optional group would match one qualifier only; the repeated group matches any sequence of
them, so `ignore instructions`, `ignore previous instructions`, `ignore all prior
instructions`, and `ignore all previous instructions` are all recognized. Because `\s+`
absorbs arbitrary whitespace, irregular spacing between words does not evade the filter.
The trailing `.*` consumes the remainder of the directive, so the payload following the
trigger phrase is removed along with it.

Four additional patterns cover complementary phrasings:

| Pattern | Intercepts |
| --- | --- |
| `(?i)system\s+prompt.*` | Attempts to address or restate the system prompt. |
| `(?i)override\s+(decision\|rules).*` | Explicit instructions to override policy. |
| `(?i)and\s+return\s+approved.*` | Attempts to dictate the committee's verdict. |
| `(?i)and\s+approve.*` | Shorter variants of the same. |

Matching is case-insensitive throughout. Non-string input returns an empty string, and the
result is whitespace-stripped.

The patterns are anchored on the verb-object pair rather than on individual keywords, which
preserves legitimate analyst text. Notes such as *"Applicant did not ignore the payment
reminders"* or *"Follow the underwriting instructions in section 4"* pass through unmodified.

### 3.2 Fail-closed PII masking

Each masking function returns a fixed placeholder when input is absent, non-string, or does
not conform to the expected format. No branch returns an unrecognized value in the clear.

**Phone numbers** — `mask_phone` compares the substitution result against its input and
falls back to a fully redacted placeholder when the pattern did not apply:

```python
output = re.sub(r"(\+?\d{2}\s?\d{2}\s?)\d{5}(-\d{4})", r"\1*****\2", phone)
return output if output != phone else "+55 ** *****-****"
```

`re.sub` returns its input unchanged when no match occurs, so an equality check is a
reliable signal that masking did not take effect. The fallback ensures a number stored in an
unanticipated format is redacted in full rather than emitted verbatim.

| Input | Output |
| --- | --- |
| `+55 11 98765-4321` | `+55 11 *****-4321` |
| `11987654321` | `+55 ** *****-****` |
| `""`, `None`, non-string | `+55 ** *****-****` |

**CPF** — `mask_cpf` strips non-digits and exposes only the two middle blocks of a valid
eleven-digit document. Any other digit count is fully masked, and absent or non-string input
returns `N/A`.

| Input | Output |
| --- | --- |
| `123.456.789-01` | `***.456.789-**` |
| `12345678901` | `***.456.789-**` |
| `123` | `***.***.***-**` |
| `""`, `None`, non-string | `N/A` |

**Email** — `mask_email` preserves the first and last characters of the local part and the
domain, masking the interior. Local parts of two characters or fewer collapse to a single
revealed character.

| Input | Output |
| --- | --- |
| `caroline@example.com` | `c******e@example.com` |
| `ab@b.com` | `a*@b.com` |
| Missing or malformed | `m***d@example.com` |

### 3.3 Parameterized data access

`get_sanitized_customer_data` binds the customer identifier as a query parameter rather
than interpolating it into the SQL string, and maps the result through the masking
functions above before returning. A regression to string interpolation is caught by a
dedicated assertion in the test suite.

### 3.4 Scope

Pattern-based filtering addresses known instruction-override phrasings and is intended as
one layer of defense rather than a complete guarantee; novel paraphrases fall outside its
reach. It is most effective combined with the controls already present in the pipeline:
constrained agent tool surfaces, deterministic policy thresholds in
`UnderwritingPolicy` that are evaluated independently of any LLM output, and masking applied
before data reaches a prompt. Extending the suite to the API and orchestration layers, as
outlined in section 2, is the next step in that direction.
