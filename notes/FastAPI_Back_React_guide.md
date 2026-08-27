# FastAPI Backend & React Frontend Integration Guide

> [!abstract] Architectural Overview
> **Backend Architecture:** FastAPI + DuckDB + Pydantic Boundaries + Llama 3 Multi-Agent Use Cases.
> **Frontend Architecture:** Vite (React) + Recharts + CSS Variable Dual Theme Context.
> **Communication Protocol:** REST over HTTP (`http://127.0.0.1:8000`).

---

## API Endpoint to React Component Map

| FastAPI Endpoint | HTTP Verb | React Component Source | Purpose |
| :--- | :--- | :--- | :--- |
| `/customers` | `GET` | `<Navbar />` | Populates the top dropdown selector |
| `/customers/{id}` | `GET` | `<CustomerDrawer />` | Loads detailed PII & financial metrics |
| `/customers/{id}/audit` | `POST` | `<CustomerDrawer />` | Triggers the 3-Agent Llama 3 audit execution |
| `/api/dashboard/kpis` | `GET` | `<KPICards />` | Renders top executive summary metrics |
| `/api/dashboard/risk-profile` | `GET` | `<ChartsGrid />` | Feeds Recharts Bar, Donut, and Scatter plots |
| `/api/dashboard/hitl-queue` | `GET` | `<ExceptionQueue />` | Renders Human-in-the-Loop review table |
| `/api/dashboard/override/{id}` | `PATCH` | `<ExceptionQueue />` | Allows underwriter to manually resolve flagged cases |

---

## Data Flow Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 REACT FRONTEND (Vite)                                  │
│                                                                                        │
│   ┌──────────────┐     ┌──────────────┐     ┌───────────────┐     ┌────────────────┐   │
│   │  Navbar.jsx  │     │ KPICards.jsx │     │ChartsGrid.jsx │     │ ExceptionQueue │   │
│   └──────┬───────┘     └──────┬───────┘     └───────┬───────┘     └───────┬────────┘   │
└──────────┼────────────────────┼─────────────────────┼─────────────────────┼────────────┘
           │ GET /customers     │ GET /kpis           │ GET /risk-profile   │ GET /hitl-queue
           │                    │                     │                     │ PATCH /override/{id}
┌──────────▼────────────────────▼─────────────────────▼─────────────────────▼────────────┐
│                                FASTAPI BACKEND (main.py)                               │
│                                                                                        │
│  • Validates Pydantic Boundaries (`CustomerProfileResponse`, `HumanOverrideRequest`)     │
│  • Executes `RunRiskAuditUseCase()` via Llama 3 Agents                                 │
│  • Queries DuckDB via `src/infra/database/database.py`                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘