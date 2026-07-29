# Phase 1 Notes: Project Architecture & Environment Setup

```text
financial-risk-ai-pipeline/
├── data/                  # Dynamic synthetic datasets and DuckDB storage
├── models/                # Serialized model artifacts (.joblib)
├── src/                   # Core application source code
│   ├── config.py          # Centralized configuration & environment flags
│   ├── database.py        # Embedded DuckDB database connector
│   ├── generate_data.py   # Synthetic data generation engine
│   ├── credit_risk_model.py # ML model class implementation
│   ├── train_model.py     # Training, evaluation & persistence execution
│   └── security.py        # PII masking & prompt injection defenses
├── tests/                 # System test suites
├── requirements.txt       # Managed dependency versions
└── README.md              # Project overview and pipeline documentation
```

## 1. What Was Built & How It Is Organized

To keep the pipeline clean and maintainable, the project structure isolates configuration, storage, logic, and tests into dedicated folders:

* **Source Directory (`src/`):** Houses Python modules responsible for data generation, database connections, model training, and security guardrails.
* **Data Folder (`data/`):** Holds raw generated CSV files (`customers.csv`) and the embedded analytical database (`financial_risk.duckdb`).
* **Models Directory (`models/`):** Stores serialized machine learning artifacts (like `.joblib` model files) so they can be reused without retraining.
* **Configuration (`src/config.py`):** Serves as a single control panel for system-wide flags, like toggling privacy masking on or off.

---

## 2. Setting Up the Virtual Environment & Dependencies

To ensure the project runs smoothly across different computers without package conflicts, virtual environment isolation is established:

```bash
# Create virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
# (Confirmation: Prompt should now display '(venv)' at the start)

# Prevent Git from tracking package files
echo "venv/" >> .gitignore
```

### Dependency Management (`requirements.txt`)

Create a `requirements.txt` file in the project root directory with the core dependencies required for data processing, machine learning, analytical storage, and security testing:

```text
pandas
duckdb
scikit-learn
xgboost
faker
joblib
```

To install all dependencies inside the active virtual environment:

```Bash
pip install -r requirements.txt
```

## 3. Main Problems Solved & Lessons Learned

| Issue & Error Message | Root Cause | Fix / Implementation |
| :--- | :--- | :--- |
| **`FileNotFoundError` on cross-platform paths** <br> `FileNotFoundError: [Errno 2] No such file or directory: 'data/customers.csv'` | Hardcoded Unix-style relative strings break when scripts execute from nested subdirectories or different OS environments. | Refactored setup script to use dynamic base pathing with `pathlib`:<br>```python<br>from pathlib import Path<br>BASE_DIR = Path(__file__).resolve().parent.parent<br>DATA_PATH = BASE_DIR / "data" / "customers.csv"<br>``` |
| **Dependency pollution / Module errors** <br> `ModuleNotFoundError: No module named 'duckdb'` | Execution defaulted to system Python (`/usr/bin/python3`) instead of the isolated environment binary. | Standardized run instructions to explicitly source `venv` and added a check inside `config.py` to assert runtime environment: <br>```python<br>import sys<br>assert sys.prefix != sys.base_prefix, "Run inside venv!"<br>``` |
