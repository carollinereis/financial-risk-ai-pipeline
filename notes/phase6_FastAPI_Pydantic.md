## Phase 6: API Layer & Contracts (FastAPI + Pydantic)

### Overview

Here the core Domain Entities and Infrastructure tools were encapsulated into a RESTful API using FastAPI and Pydantic DTOs.

### Key Highlights
* **DTO Schemas (`src/api/schemas.py`)**: Used Pydantic `BaseModel` to enforce strict contracts for requests and responses, preventing schema drift between backend and frontend.
* **CORS Configuration**: Enabled cross-origin requests specifically for local Vite React development (`http://localhost:5173`).
* **Interactive Documentation**: Leveraged OpenAPI / Swagger UI (`/docs`) for direct API testing and endpoint validation.

### API Endpoints
* `GET /customers` — Returns list of available customers for dropdown selection.
* `GET /customers/{id}` — Fetches customer profile metrics with sanitized/masked PII.
* `POST /customers/{id}/audit` — Triggers the multi-agent LLM risk audit committee execution.


</details>

<br>

<details>
<summary><b> View FastAPI Swagger UI Audit Endpoint Test</b></summary>

<br>

#### Verification Screenshot

[IMG 1](./images/post_img1.png)

[IMG 2](./images/post_img2.png)

</details>


