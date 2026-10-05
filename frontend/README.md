# Risk AI Dashboard

This is the frontend for a multi-agent credit underwriting engine. Underwriters use it to keep an eye on the portfolio, look into any applicant, run the AI committee on them, and step in when the agents disagree.

[1. Dashboard Overview](./img/dashboard-overview.png)

[2. Hard Policy Override Demonstration](./img/hard-policy-rejection-Alice.png)

[3. Customer Agent Drawer](./img/customer-drawer.png)

[4. Customer Full Agent Report](./img/full-agent-report.png)

[5. Dark mode - Approved Customer](./img/approved-customer-dark-mode.png)

[6. Underwriting Policy for Reference](./img/Underwriting-Policy-Reference.png)

[7. Document Intelligence](./img/document-intelligence.png)

[8. Combined Report](./img/combined-report.png)

## What it does

- **Portfolio overview:** Track real-time KPIs, approve/reject splits, default risk by credit score band, and Top 5 lists for riskiest applicants and largest loans.
- **Customer view:** Inspect applicant profiles, score history, agent recommendations, and portfolio comparisons via sidebar selection or `⌘K` search.
- **On-demand audits:** Saved reports load instantly; fresh three-agent AI audits run on demand.
- **Human in the loop:** Split agent decisions automatically route to an exception queue where overrides require a logged reason and operator attribution.
- **Document Intelligence:** Each customer has one generated mock loan contract; a single click extracts borrower name, loan amount, rate, term, and signature status, and lists any document issues (rate above the legal cap, a missing signature, a borrower name mismatch) alongside an executive summary. It checks the contract's paperwork only. It doesn't evaluate credit risk, which stays the committee's job.
- **Combined report:** Once both the committee audit and document extraction exist for a customer, preview a combined report and download it as a PDF, generated client-side from the rendered preview so the download always matches what was reviewed on screen.

## Prerequisites

* **Node.js:** `v20.19+` or `v22.12+`
* **FastAPI Backend:** Running on `http://localhost:8000`. See [`/src`](../src) for setup (Postgres, migrations, model training, Ollama).

## Getting Started

1. **Set up and run the backend first.** Follow [`/src`](../src)'s Getting Started (Postgres, migrations, data, and `uvicorn src.api.main:app --reload`).

2. **Run the frontend** (from this directory):
   ```bash
   npm install
   npm run dev
   ```

3. Open `http://localhost:5173` in your browser. Interactive API documentation is available at `http://localhost:8000/docs` while the backend is active.


## Tech Stack

* **Core:** React 19, Vite 8, Recharts, Lucide React
* **Reporting:** jsPDF + html2canvas for client-side PDF export of the combined report
* **Database:** PostgreSQL 16 (via Docker)
* **Styling & Config:** Theme colors managed via CSS variables (`src/styles/theme.css`); backend endpoints set in `src/config.js`.