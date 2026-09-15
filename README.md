# Financial Risk AI Pipeline 

This project was born out of curiosity about how to build an end-to-end platform using generative AI and machine learning inside financial institutions.

The financial risk pipeline is designed to streamline a risk manager's decision-making process by using a three-agent committee:
* **Quantitative Agent:** Evaluates hard metrics against risk thresholds.
* **Qualitative Agent:** Analyzes unstructured underwriter notes for behavioral signals.
* **CRO (Chief Risk Officer) Agent:** Weighs both quantitative and qualitative reports to make a final binding decision.

By automating this multi-layered analysis, bank employees save significant time by focusing only on cases that genuinely require manual underwriter review.

---

## How It Works

* **Agent Orchestration & AI Guardrails:** LangChain orchestrates the multi-agent committee workflow, managing agent state transitions, memory, and prompt pipelines. Strict system prompt constraints and structured Output Parsers enforce deterministic JSON outputs, eliminating LLM hallucinations and grounding every decision in factual data.
* **Machine Learning Foundation:** An XGBoost model was trained to predict the probability of default, complementing the LLM committee with a statistically rigorous quantitative score.
* **Regulatory & Risk Guidelines:** The system follows FICO guidelines to evaluate key risk thresholds including credit score, debt-to-income (DTI) ratio, payment delinquencies, and XGBoost risk scores.
* **Privacy & Security Guardrails:** Customer records pass through a sanitization layer before reaching the LLM. Sensitive PII, such as Brazilian CPFs, email addresses, and phone numbers is automatically masked, and potential prompt injection attempts are redacted.
* **Data Architecture:** The system uses DuckDB as an in-memory transactional database. It includes structured test scenarios engineered for definitive approval or rejection outcomes, alongside synthetic data simulating real-world portfolio analytics.
* **Database & Persistence Layer:** Operates DuckDB for in-memory analytical scenario testing combined with a containerized PostgreSQL 16 database for frontend transactional state and application data.
---

## Tech Stack

* **Backend & Agent Committee:** Python, FastAPI, LangChain, XGBoost, Llama 3.1 (Ollama)
* **Database & Infrastructure:** DuckDB, PostgreSQL 16 (Dockerized)
* **Frontend:** React, Vite, Recharts, Lucide React
  👉 *See the [`/frontend`](./frontend) directory for UI, architecture overview, and local setup instructions.*
