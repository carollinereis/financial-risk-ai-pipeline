# Backend

This service powers the Financial Risk AI Pipeline: the multi-agent AI committee, the machine learning risk model, the document verification workflow, and the APIs the frontend uses.

## What It Does

When an underwriter runs an audit on a customer, three stages run:

1. **XGBoost Risk Scoring:** The customer's financial data is scored by a trained XGBoost model to estimate the probability of default.
2. **Three-Agent AI Committee:** Reviews the case and reaches a decision:
   - **Quantitative Agent:** Checks hard financial metrics (credit score, DTI, the XGBoost score) against underwriting thresholds.
   - **Qualitative Agent:** Reviews the underwriter's notes for behavioral risk signals.
   - **CRO Agent:** Weighs both reports and issues the final recommendation: `APPROVED`, `REJECTED`, or `MANUAL REVIEW REQUIRED`.
3. **Document Intelligence:** Reads the customer's mock loan contract and flags discrepancies, such as a rate above the legal cap, a missing signature, or a borrower name that doesn't match the customer on file. This runs independently of the committee above and never influences the credit decision.

## How the System Prevents AI Hallucination

Local LLMs (Llama 3.1 via Ollama) can occasionally misapply a rule or misattribute a result. The pipeline doesn't take the model's output at face value. Two layers guard against it:

**Before the LLM runs:** Values the model would otherwise have to calculate itself, such as the risk band, which policy was triggered, and which exact metric breached a threshold, are calculated deterministically in Python first and passed into the prompt as a fact to repeat, not derive.

**After the LLM responds:** Its answer is checked against those same facts. If it disagrees with the underlying numbers (for example, the CRO rejects a case with no real policy breach, or approves one that should have been an automatic rejection), the system overrides the decision and routes the case to a human instead.

This combination caught a real bug during development: the CRO agent occasionally attributed a rejection to DTI when the credit score was the actual cause. The fix was supplying the pre-calculated, per-metric breakdown directly, plus a deterministic check afterward that catches the case if the model still gets it wrong.

The Document Intelligence name-check follows the same principle: matching the extracted borrower name against the registered customer is a plain Python comparison, not something left to the LLM's judgment.

> **Fail-closed by default:** When an AI output doesn't parse, or a document doesn't extract cleanly, the system doesn't default to approval. It's flagged for human review instead.

## Model Provider Flexibility

Ollama was chosen for this project because it is free and runs entirely locally, a practical fit for a mock project with no cloud budget, not a technical requirement. The LLM calls go through LangChain, so swapping the model (to OpenAI, Anthropic, or another LangChain-supported provider) means changing the client configuration in one place, not rewriting the application logic.

## Testing Strategy

Agent behavior is tested across three layers:
- **Wiring tests:** Mock the LLM entirely and verify the code calls it with the right inputs. Fast, run by default.
- **Prompt tests:** Verify the prompt text itself hasn't drifted. Also fast.
- **Integration tests:** Call the real Ollama model and check its actual output. Slower, marked `@pytest.mark.integration`, and skipped by default (`pytest -m integration` to run them).

## Known Limitations

- Llama 3.1 doesn't always follow formatting instructions precisely. Occasional filler or stray commentary can appear in a report.
- The guardrails above reduce hallucination; they don't eliminate it. At least one case was found where the model still contradicted its own pre-calculated data despite the fix, which is exactly why a human-review path always exists.

## Prerequisites

* **Python:** 3.12+
* **Docker & Docker Compose:** for the Postgres database
* **Ollama:** running locally with `llama3.1` pulled (`ollama pull llama3.1`)

## Getting Started

1. **Install dependencies:**
   ```bash
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Add a `.env`** in the repo root with the Postgres settings referenced in `docker-compose.yml`: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`, and `DATABASE_URL`.
3. **Start Postgres and apply migrations:**
   ```bash
   docker compose up -d postgres
   alembic upgrade head
   ```
4. **Generate data, train the model, and generate mock documents:**
   ```bash
   python -m src.infra.database.generate_data
   python -m src.infra.ml.train_model
   python -m src.infra.database.generate_mock_documents
   python -m src.infra.database.postgres.seed
   ```
5. **Run the API:**
   ```bash
   uvicorn src.api.main:app --reload
   ```
6. Open `http://localhost:8000/docs` for interactive API docs, or see [`/frontend`](../frontend) to run the dashboard.

## Tech Stack

* Python
* FastAPI
* LangChain
* Pydantic
* XGBoost
* Llama 3.1 (via Ollama)
* DuckDB
* PostgreSQL 16
