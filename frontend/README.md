# Financial Risk AI Pipeline — Governance Dashboard (Frontend)

React + Vite interface for the multi-agent underwriting engine. Underwriters search the
portfolio, read saved committee reports, and record human overrides against the FastAPI
backend.

## Quick Start

```bash
npm install
npm run dev          # http://localhost:5173
```

Requires **Node 20.19+ or 22.12+** and the backend running on `http://localhost:8000`:

```bash
uvicorn src.api.main:app --reload    # from the repository root
```

| Script | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server on :5173 |
| `npm run build` | Production bundle to `dist/` |
| `npm run preview` | Serve the built bundle |
| `npm run lint` | oxlint over `src/` |

## Tech Stack

| Concern | Choice |
| --- | --- |
| Framework | React 19.2 |
| Build | Vite 8.2 |
| Charts | Recharts 3.10 |
| Icons | lucide-react |
| Lint | oxlint |
| HTTP | native `fetch` |
| Styling | Inline style objects + CSS custom properties (`src/styles/theme.css`) |

Theming is token-based: every colour resolves from `--bg`, `--surface`, `--accent`,
`--status-*` variables that swap under `[data-theme]`. Charts read the same tokens
through `useChartColors`, so light and dark stay in step.

## Features

| Feature | Behaviour |
| --- | --- |
| **Quick search** (`⌘K` / `Ctrl K`) | Autocomplete over name or `#ID`, keyboard-navigable, with an Analyzed / Not Analyzed badge per result |
| **Customer registry** | Full roster modal opened from the Total Customers card; filter, search, and per-row CRO verdict, split-committee and drift markers |
| **Instant report replay** | Opening a client renders the saved committee transcript from DuckDB — no agent run, no LLM cost |
| **Explicit re-run** | "Re-run Multi-Agent Audit" is the only path that invokes the pipeline |
| **Verdict basis** | Each agent vote carries the reasoning that produced it, including any deterministic policy override of the agent's own prose |
| **Drift & staleness** | Warns when the model has re-scored a client since the audit, or when a report has aged past 14 days |
| **Exception queue** | Committee disagreements pending review; overrides require a rationale and an underwriter name for the audit trail |
| **Coverage reporting** | KPI row states how much of the portfolio has actually been through the committee, so portfolio rates carry their denominator |
| **Theme toggle** | Sun / Moon control, persisted to `localStorage`, defaults to the OS preference |

## Structure

```
src/
├── App.jsx                    # Roster + KPI fetch, drawer/registry orchestration
├── config.js                  # API base URL
├── components/
│   ├── Navbar.jsx             # Header shell
│   ├── CustomerSearch.jsx     # ⌘K autocomplete
│   ├── KPICards.jsx           # Executive KPI row
│   ├── CustomerRegistry.jsx   # Full-roster modal
│   ├── CustomerDrawer.jsx     # Profile, saved audit, re-run
│   ├── AgentReport.jsx        # Renders the agents' loose markdown
│   ├── ChartsGrid.jsx         # Decision split + score distribution
│   ├── ExceptionQueue.jsx     # HITL review and overrides
│   ├── PolicyReference.jsx    # Enforced underwriting thresholds
│   └── ThemeToggle.jsx
├── context/ThemeContext.jsx
├── hooks/useChartColors.js
└── styles/theme.css
```

## API Consumed

| Method | Endpoint | Used by |
| --- | --- | --- |
| `GET` | `/api/dashboard/customer-registry` | Roster for search, charts, registry |
| `GET` | `/api/dashboard/kpis` | KPI row |
| `GET` | `/api/dashboard/decision-distribution` | Decision donut |
| `GET` | `/api/dashboard/agent-consensus` | Consensus subtitle |
| `GET` | `/api/dashboard/policy-reference` | Policy thresholds |
| `GET` | `/api/dashboard/hitl-queue` | Exception queue |
| `PATCH` | `/api/dashboard/override/{application_id}` | Underwriter override |
| `GET` | `/customers/{id}` | Drawer profile |
| `GET` | `/customers/{id}/audit` | Saved transcript (read-only) |
| `POST` | `/customers/{id}/audit` | Fresh committee run |
