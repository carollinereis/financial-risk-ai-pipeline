## 🚨 Phase 1: Tier 1 — Stop Fabricated Data & Fix Fallbacks

[√ ] Fix KPICards.jsx Nullish Coalescing:

[√ ] Swap || to ?? for approvalRate and avgTime so legitimate 0 values don't trigger hardcoded fallbacks (65%, 4.2).

[ √] Replace misleading fallback numbers with explicit empty states (-- or 0).

[√ ] Fix ChartsGrid.jsx Hardcoded Donut Chart:

[√ ] Delete the static Approved: 65 / Rejected: 35 array.

[√ ] Wire the chart to fetch real data from GET /api/dashboard/agent-consensus.

[√ ] Remove Bar Chart Phantom Bars:

[√ ] Delete || 1, || 2 fallbacks on the credit score distribution so empty bands render at 0.

## 🛡️ Phase 2: Tier 2 — Secure CustomerDrawer.jsx & PII

[ ] Prevent Cross-Customer PII Leaks:

[ ] Execute setProfile(null) and setAudit(null) immediately inside useEffect when customerId changes.

[ ] Add Request Cancellation:

[ ] Implement AbortController in the profile fetch to discard out-of-order responses during fast switching.

[ ] Add Network & Audit Safeguards:

[ ] Add if (!res.ok) status checks on all fetch calls to handle 404/500 errors gracefully.

[ ] Add AbortSignal.timeout(30000) (30s) to the /audit POST request so a hanging Ollama instance doesn't lock the button forever.

[ ] Fix Typo:

[ ] Change pb: '10px' to paddingBottom: '10px' in drawerStyles.header.

## 🔄 Phase 3: Tier 3 — Wire Unused Backend Endpoints & HITL Workflow
[ ] Connect Human-in-the-Loop (HITL) Queue:

[ ] Point ExceptionQueue.jsx to fetch directly from GET /api/dashboard/hitl-queue instead of client-side filtering (credit_score < 600).

[ ] Build Underwriter Override Action:

[ ] Add an override action trigger/modal calling PATCH /api/dashboard/override/{id} with custom underwriter notes.

[ ] Fix Navbar Selector:

[ ] Wire selectedId in Navbar.jsx to update inspectedId so selecting a client opens their drawer.

[ ] Wire Remaining Analytics:

[ ] Connect GET /api/dashboard/agent-analytics.

🧹 Phase 4: Housekeeping & Clean Architecture
[ ] Centralize Configuration:

[ ] Create src/config.js exporting API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000' and import it everywhere.

[ ] Add Top-Level Error Boundary:

[ ] Wrap <App/> in a React Error Boundary to prevent full white-screen crashes from malformed payloads.