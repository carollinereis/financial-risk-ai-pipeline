import os
from pathlib import Path

from dotenv import load_dotenv

# Project Root Resolution (3 levels up: infra -> src -> root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Populates LANGSMITH_TRACING / LANGSMITH_API_KEY / LANGSMITH_PROJECT for ChatOllama tracing.
load_dotenv(BASE_DIR / ".env")

# Core Directories
DATA_DIR = BASE_DIR / "src" / "infra" / "data"

# File Paths (Single Source of Truth)
DUCKDB_PATH = DATA_DIR / "financial_risk.duckdb"
CSV_PATH = DATA_DIR / "customers.csv"
MODEL_PATH = BASE_DIR / "src" / "infra" / "ml" / "models" / "xgb_model.json"

# Postgres (additive, alongside DuckDB): borrower registry, score history, async task state.
DATABASE_URL = os.getenv("DATABASE_URL")
