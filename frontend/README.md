# Financial Risk AI Pipeline: Governance Dashboard

This is the frontend for a multi-agent credit underwriting engine. Underwriters use it to keep an eye on the portfolio, look into any applicant, run the AI committee on them, and step in when the agents disagree.

![Dashboard](docs/dashboard.png)

## What it does

- **Portfolio overview:** KPIs, the approve/reject split, default risk by credit score band, and Top 5 lists of the riskiest applicants and the largest loans.
- **Customer view:** pick anyone from the sidebar, ⌘K search, or a Top 5 list to see their profile, score history, how they compare to the portfolio, and each agent's recommendation.
- **On-demand audits:** saved reports load instantly. A fresh three-agent audit only runs when you ask for one.
- **Human in the loop:** cases where the agents disagree go to an exception queue, and every override needs a reason and a name.

## Running it locally

You need Node 20.19+ or 22.12+ and the FastAPI backend running on `localhost:8000`.

```bash
# from the repository root
uvicorn src.api.main:app --reload

# from this folder
npm install
npm run dev        # http://localhost:5173
```

Fresh audits also need Ollama running locally with Llama 3.1. The API docs are at `localhost:8000/docs` while the backend is running.

## Stack

React 19, Vite 8, Recharts, and lucide-react. Theme colors come from CSS variables in `src/styles/theme.css`, and the backend URL is set in `src/config.js`.