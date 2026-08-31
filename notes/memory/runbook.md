# Runbook — Local Startup

Operational reference for booting the stack. All commands run from the repository root.

## Ports & Processes

| Service               | Command                             | Port  | Required           |
| --------------------- | ----------------------------------- | ----- | ------------------ |
| FastAPI backend       | `uvicorn src.api.main:app --reload` | 8000  | Yes                |
| Vite frontend         | `cd frontend && npm run dev`        | 5173  | Yes                |
| Ollama (Llama 3.1)    | `ollama serve`                      | 11434 | Only for AI audits |
| Streamlit (legacy UI) | `streamlit run app.py`              | 8501  | No — parallel path |

- CORS on the API allows `5173`, `127.0.0.1:5173`, and `3000` only. Serving the frontend from another port requires editing `allow_origins` in `src/api/main.py`.
- Frontend API target resolves from `VITE_API_BASE`, defaulting to `http://localhost:8000` (`frontend/src/config.js`).

## Standard Startup — Three Terminals

```bash
# Terminal 1 — Ollama (skip if no audits will be run)
ollama serve
ollama pull llama3.1          # first run only

# Terminal 2 — Backend
source venv/bin/activate
uvicorn src.api.main:app --reload

# Terminal 3 — Frontend
cd frontend
npm install                   # first run only
npm run dev
```

Dashboard: `http://localhost:5173` · API docs: `http://localhost:8000/docs`

## First-Run Order

Order matters — each step depends on the previous one.

| # | Step | Command |
| --- | --- | --- |
| 1 | Create venv | `python3 -m venv venv && source venv/bin/activate` |
| 2 | Install Python deps | `pip install -r requirements.txt` |
| 3 | Generate seed data | `python -m src.infra.database.generate_data` |
| 4 | Init DB, train model, write scores | `python -m src.infra.ml.train_model` |
| 5 | Install frontend deps | `cd frontend && npm install` |
| 6 | Start services | See *Standard Startup* above |

Artifacts produced: `src/infra/data/customers.csv`, `src/infra/data/financial_risk.duckdb`, `src/infra/ml/models/xgb_model.json`.

## Environment

| Item | Value |
| --- | --- |
| Python | 3.12.13 (`venv/`) |
| Node | v25.6.1 |
| npm | 11.9.0 |
| LLM | `llama3.1` via Ollama, `temperature=0.0` |

## Verification

```bash
curl -s http://localhost:8000/customers | head -c 200          # backend + DB
curl -s http://localhost:8000/api/dashboard/kpis               # aggregates
curl -s http://localhost:8000/api/dashboard/policy-reference   # policy thresholds
curl -s http://localhost:11434/api/tags                        # Ollama reachable
```

## Quality Gates

```bash
ruff check . && ruff format .        # Python lint + format (ruff.toml)
python -m pytest tests/ -q           # test suite
cd frontend && npm run lint          # oxlint
cd frontend && npm run build         # production build check
```

## Maintenance

```bash
python -m src.infra.security.security   # PII-masking / prompt-injection checks
python -m src.infra.ml.train_model      # retrain and rewrite risk scores
cd frontend && npm run preview          # serve the built bundle
```

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Dashboard shows "Backend unreachable" | API not running | Start uvicorn in Terminal 2 |
| Charts empty, KPIs zero | DB not seeded or model not trained | Run first-run steps 3–4 |
| Audit hangs indefinitely | Ollama down or model not pulled | `ollama serve`, then `ollama pull llama3.1` |
| `ModuleNotFoundError: src` | Run from a subdirectory | Run all Python from the repository root |
| DuckDB file-lock error | Two writers open at once | DuckDB is single-writer — stop the other process |
| CORS error in browser console | Frontend on an unlisted port | Add the port to `allow_origins` in `src/api/main.py` |

## Constraints

- Python modules run from the repository root using absolute `src.*` imports.
- DuckDB is single-writer — only one write connection may be open at a time.
- `BASE_DIR` imports exclusively from `src/infra/config.py`.
- Audits require Ollama; every other dashboard surface works without it.


XGBoost Risk Score > 0.50 indicates HIGH PROBABILITY OF DEFAULT.