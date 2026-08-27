# Dashboard Technical Specification

## Data Requirements (FastAPI Endpoints)
- `GET /api/v1/metrics/kpis` -> Approval rates, R$ volume, avg decision latency.
- `GET /api/v1/metrics/agents` -> Consensus %, agent divergence breakdown.
- `GET /api/v1/metrics/risk` -> Rating band distribution (A-F), DTI matrices.
- `GET /api/v1/audit/exceptions` -> HITL queue for split decisions (2 vs 1).

## Currency & Localization
- **Currency:** BRL (R$)
- **Locale:** `pt-BR`