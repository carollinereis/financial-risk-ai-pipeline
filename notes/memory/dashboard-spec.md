# Dashboard rework brief

This is the Financial Risk AI Pipeline dashboard: portfolio KPIs, a customer registry, a customer profile drawer, and a multi-agent committee audit (quant, qual, and CRO agents orchestrated by run_audit_committee). The data comes from DuckDB, and default probability comes from the XGBoost model.

We are reorganizing the dashboard around one idea: a customer list on the left that drives what the main area shows. This is the same pattern as a Power BI report where you click a name in a slicer and the visuals update. A screenshot of such a report is included as a reference. Use it for the layout pattern only. Do not copy its colors, gold theme, logos, or branding. Keep this app's existing visual style and its light/dark theme.

![image](/notes/images/dashboard-idea.png)

Ground rules (apply to every phase)
Use only data that already exists in the codebase and database. Do not add mock, placeholder, or hardcoded data. If a chart would need a field that doesn't exist, tell me instead of inventing it.
Do not change agent logic, the ML model, or the database schema without asking me first.
Keep these as they are: the KPI cards, the customer profile drawer (including its committee report), the Evaluated Customers Registry modal, the Underwriting Policy panel, the Exception Queue, and the theme toggle.
Match the existing styling. Do not introduce a new UI library, a new color palette, or new fonts.
Stop at the end of each phase. Summarize what changed, list the files you touched, and wait for my go-ahead.
Target layout
+---------------------------------------------------------------------------+
| Financial Risk AI Pipeline                    [search ⌘K]       [theme]   |
+---------------------------------------------------------------------------+
| [Total customers] [Coverage] [Avg credit score] [Approval rate] [Time]    |
|   ^ unchanged, always portfolio-level, updates after every audit          |
+----------------+----------------------------------------------------------+
| Customers      |  NO CUSTOMER SELECTED -> portfolio view                  |
| [search...]    |  [Decision split donut]   [Default prob. by score band]  |
| All / Analyzed |  [Top 5 highest default probability] [Top 5 largest loans]|
| / Not analyzed |                                                          |
| -------------- |  CUSTOMER SELECTED -> customer view                      |
| > Diana Prince |  +----------------- Applicant card -------------------+  |
|   #104   790   |  | name, #id, masked CPF, requested loan, income,     |  |
|   Approved     |  | DTI, credit score, ML default probability,         |  |
|   David W.     |  | committee verdict badge (or "Not analyzed")        |  |
|   #107   538   |  | [Run committee audit]   [Open full report]         |  |
|   Not analyzed |  +----------------------------------------------------+  |
|   ...scrolls   |  [Credit score history]   [Risk score history]           |
|                |  [Customer vs portfolio]  [Agent recommendations]        |
+----------------+----------------------------------------------------------+
| Underwriting policy (collapsible, unchanged)                              |
| Exception queue (unchanged, but must stay in sync with audits)            |
+---------------------------------------------------------------------------+
Behavior rules

One selected customer, many entry points. There must be a single piece of state (for example selectedCustomerId) that every entry point sets: clicking a row in the sidebar, choosing a result in the header search, and clicking "Open Profile" in the registry modal. Remove the "Client for score charts" dropdown, because the sidebar replaces it. Selecting a customer highlights their row in the sidebar and switches the main area to the customer view. A clear button (and the Esc key) returns to the portfolio view. Nice to have: reflect the selection in the URL (?customer=104) so a refresh keeps it.

KPI cards stay portfolio-level. Selecting a customer does not filter the KPI cards. They always describe the whole portfolio.

Portfolio view (nothing selected). No empty "select a client" boxes. Show portfolio charts built from existing data. Keep the decision split donut. Add a chart of average default probability by credit score band (or by risk rating, if that field exists). Add a Top 5 list of the highest default probability and a Top 5 of the largest requested loans. If any of these can't be built from existing data, say so and propose an alternative.

Customer view. Show the applicant card with the same fields the profile drawer uses. Move the existing credit score history and risk score history charts here. Add a "Customer vs portfolio" comparison of credit score, DTI, and default probability against the portfolio average. Add an "Agent recommendations" panel that shows each agent's recommendation and the CRO's final verdict from the saved audit. If there is no audit yet, that panel shows a short message and the "Run committee audit" button instead of an empty chart. "Open full report" opens the existing profile drawer for that customer.

Sidebar list. It is searchable by name or ID, with All / Analyzed / Not analyzed filters (the same logic as the registry modal). Each row shows the name, ID, credit score, and a status badge. It scrolls independently of the main area.

The "Run committee audit" flow

This is the most important part to get right.

The button in the applicant card and the existing button in the drawer must call the same handler. That handler goes through the existing orchestrator, run_audit_committee. Do not write new agent logic or a second orchestration path. If there is a manual agent-invocation path in app.py that duplicates the orchestrator, flag it; don't build on it.
If the frontend has no way to trigger an audit yet, propose an endpoint or function that wraps run_audit_committee and saves the result using the existing save path. Show me the proposal before building it.
While it runs (about 10 seconds, since the agents run on local Llama via Ollama): disable the button, change its label to "Running audit…", and prevent double submits. If the orchestrator exposes per-agent progress, show it. Otherwise, show a single progress state.
On success, update the following without a full page reload: the applicant card's verdict badge, the agent recommendations panel, the KPI cards (coverage, approval rate, average decision time), the donut, the sidebar row's status, and the exception queue (add the application if the agents disagreed). Show a short confirmation with the verdict, e.g. "Audit complete: Approved".
On failure, show what failed in plain language inside the card (for example, "Couldn't reach the local model. Is Ollama running?") and include a "Try again" button. Never fail silently.
Phases

Do one phase per session and stop at the end of each one.

Phase 0: Discovery (read-only, no code changes)

Read the codebase and report back:

The frontend file structure and how it gets data (API endpoints, direct DB calls, or something else).
Every customer field that is available, and where the credit score history and risk score history data come from.
How an audit is currently triggered, saved, and read back, including whether the UI can trigger one.
Bug to investigate: the donut shows "60% agent agreement," but the exception queue says every application was unanimous. Find how each number is calculated and explain the mismatch. Don't fix it yet.
Your implementation plan for phases 1 to 4, including anything in this brief that the data can't support.
Phase 1: Selection state and layout

Add the sidebar, the single selection state wired to all entry points, the portfolio and customer view switch, and remove the dropdown.

Done when:

 Clicking a sidebar row, a header search result, or registry "Open Profile" all select the same customer.
 Clearing the selection returns to the portfolio view.
 Nothing else on the page broke, in both light and dark mode.
Phase 2: Applicant card and charts

Build the applicant card, the customer view charts, and the portfolio view charts.

Done when:

 There are no empty chart boxes in either view.
 Every chart is backed by real data.
 Customers without an audit show a sensible state instead of broken charts.
Phase 3: Audit flow

Implement the run-audit flow described above.

Done when:

 Running an audit on an unanalyzed customer updates the card, the agent panel, the KPIs, the donut, the sidebar status, and the exception queue with no reload.
 A double click does not start two audits.
 Stopping Ollama and clicking the button shows a clear error with a retry option.
Phase 4: Fix and polish

Fix the agreement vs. exception queue mismatch so both use one shared definition of "agents disagreed." Then check the empty states, loading states, keyboard navigation of the sidebar, and both themes. Take screenshots of both views in both themes and review them against the target layout.

