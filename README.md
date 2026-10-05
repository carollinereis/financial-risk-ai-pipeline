# Financial Risk AI Pipeline 

This project was born out of curiosity about how to build an end-to-end platform using generative AI and machine learning inside financial institutions.

It automates a loan risk review using a three-agent AI committee (Quantitative, Qualitative, and CRO) backed by an XGBoost default-risk model, plus a separate Document Intelligence step that reads mock loan contracts and flags paperwork issues. The goal: let risk managers and underwriters focus only on the cases that actually need a human look.

---

## Where to look

* **[`/src`](./src) (Backend):** The AI committee, the ML model, the anti-hallucination guardrails, the APIs, the databases. Start here to see how decisions actually get made.
* **[`/frontend`](./frontend) (Frontend):** The dashboard underwriters use to browse the portfolio, run audits, and review flagged cases.

Each has its own README with setup instructions and a closer look at how it works.

`app.py` at the repo root is an early Streamlit prototype from before the FastAPI + React app existed. It still runs, but it's no longer the active product.

---

## Tech Stack

* **Backend:** Python, FastAPI, LangChain, Pydantic, XGBoost, Llama 3.1 (via Ollama)
* **Database:** DuckDB + PostgreSQL 16 (Dockerized)
* **Frontend:** React, Vite, Recharts, Lucide React
