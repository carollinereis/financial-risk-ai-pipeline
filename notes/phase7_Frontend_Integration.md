## Phase 7: Frontend Integration (React + Vite MVP)

### Overview
Phase 2 established the client-facing user interface layer, enabling end-to-end communication between the React frontend and the FastAPI backend service over HTTP.

### Key Highlights
* **Vite + React Setup**: Scaffolded a lightweight, component-driven frontend architecture inside the `frontend/` directory.
* **API Service Abstraction (`src/services/api.js`)**: Encapsulated network request logic using `axios` to query FastAPI endpoints (`/customers`, `/customers/{id}`, and `/customers/{id}/audit`).
* **State Management**: Managed application state using React hooks (`useState`, `useEffect`) to seamlessly handle asynchronous data loading, error states, and UI reactivity.
* **Data Presentation**: Rendered real-time credit score metrics, debt-to-income (DTI) ratios, XGBoost default probabilities, sanitized PII, and multi-agent audit decisions within a consolidated risk dashboard.

### Verification Screenshot
[React Risk AI Dashboard](./images/frontEnd_test1.png)
