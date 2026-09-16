# Risk AI Dashboard

This is the frontend for a multi-agent credit underwriting engine. Underwriters use it to keep an eye on the portfolio, look into any applicant, run the AI committee on them, and step in when the agents disagree.

[Watch here - Dashboard Demo](./video/dashboard-memo.mov)

## What it does

- **Portfolio overview:** Track real-time KPIs, approve/reject splits, default risk by credit score band, and Top 5 lists for riskiest applicants and largest loans.
- **Customer view:** Inspect applicant profiles, score history, agent recommendations, and portfolio comparisons via sidebar selection or `⌘K` search.
- **On-demand audits:** Saved reports load instantly; fresh three-agent AI audits run on demand.
- **Human in the loop:** Split agent decisions automatically route to an exception queue where overrides require a logged reason and operator attribution.

## Prerequisites

* **Node.js:** `v20.19+` or `v22.12+`
* **Docker & Docker Compose:** Required to run the PostgreSQL database service.
* **FastAPI Backend:** Running on `http://localhost:8000`
* **Ollama:** Running locally with `Llama 3.1` (required for generating fresh audits)

## Getting Started

1. **Start the Database Infrastructure** (from repository root):
   ```bash
   docker compose up -d postgres
   ```

2. **Run the Backend** (from the repository root):
   ```bash
   uvicorn src.api.main:app --reload
    ```

3. **Run the Frontend** (from this directory):
    ```bash
    npm install
    npm run dev
    ```

3. Open `http://localhost:5173` in your browser. Interactive API documentation is available at `http://localhost:8000/docs` while the backend is active.


## Tech Stack

* **Core:** React 19, Vite 8, Recharts, Lucide React
* **Database:** PostgreSQL 16 (via Docker)
* **Styling & Config:** Theme colors managed via CSS variables (`src/styles/theme.css`); backend endpoints set in `src/config.js`.