# Skill: Financial Governance & Audit Dashboard

## Core Layout Requirements
1. **Executive Overview (KPI Cards):**
   - Approval Rate (% approved vs rejected/manual review).
   - Total Credit Volume (Requested vs Approved in R$).
   - Average Risk Score (Weighted portfolio risk).
   - Average Decision Time (Seconds/minutes for 3-agent pass).

2. **AI Agent Operational Analysis:**
   - Consensus / Divergence Rate (% unanimous vs HITL required).
   - Verdict Distribution (Comparative breakdown across Financial, Credit, and Behavioral agents).
   - Exception Queue (HITL review panel for divergent decisions).

3. **Risk Profile & Customer Distribution:**
   - Risk Rating Bands (Histogram/donut for Bands A through F).
   - DTI Relationship (Debt-to-Income vs Default Risk).
   - Estimated Delinquency Matrix (Accumulated default risk projection).

## Component Guidelines
- **UI Stack:** React, Tailwind CSS, Lucide Icons, Recharts (or Tremor/Chart.js).
- **State & Performance:** Derive metrics in-place or wrap heavy aggregations in `useMemo`.
- **Formatting:** Format currency using Brazilian Real (`Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })`).
- **Data Safeguards:** Always render loading skeletons and fallback states when awaiting FastAPI streams.