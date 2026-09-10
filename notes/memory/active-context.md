# Active Context

- 2026-09-10: Dashboard rework (`notes/memory/dashboard-spec.md`) Phase 0 discovery done, read-only. Root cause of donut-vs-queue mismatch found: `fetch_agent_consensus_stats` counts divergence regardless of `overridden_at`; `fetch_hitl_exception_queue` excludes overridden rows. Not fixed yet — deferred to Phase 4 per spec. Awaiting go-ahead on Phase 1 (sidebar + selection state).
- Flagged: `app.py` (legacy Streamlit) calls `run_audit_committee` directly, bypassing `RunRiskAuditUseCase`/`record_audit_results` — never persists, dead-end path, don't build the new audit UI on it.
- 2026-09-10: Phase 1 done — `selectedCustomerId` in App.jsx now the single selection state (sidebar/search/registry all set it); drawer is a separate `openReportId` opened only via "Open full report". Dropdown removed from ChartsGrid. Awaiting go-ahead on Phase 2 (applicant card + portfolio/customer charts).
