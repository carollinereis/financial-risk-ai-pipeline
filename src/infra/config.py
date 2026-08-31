from pathlib import Path

# Project Root Resolution (3 levels up: infra -> src -> root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Core Directories
DATA_DIR = BASE_DIR / "src" / "infra" / "data"

# File Paths (Single Source of Truth)
DUCKDB_PATH = DATA_DIR / "financial_risk.duckdb"
CSV_PATH = DATA_DIR / "customers.csv"
MODEL_PATH = BASE_DIR / "src" / "infra" / "ml" / "models" / "xgb_model.json"

# Feature & Privacy Flags
ENABLE_PII_MASKING = True  # Toggle True/False to control PII masking across infra
