from pathlib import Path

# --- Security & Governance Settings ---
# Set to True to sanitize profiles and redact PII for LLM consumption.
# Set to False during development/debugging to retain raw mock data.
ENABLE_PII_MASKING: bool = True

# --- File System Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

DUCKDB_PATH = DATA_DIR / "financial_risk.duckdb"
MODEL_PATH = MODELS_DIR / "xgb_v1.json"