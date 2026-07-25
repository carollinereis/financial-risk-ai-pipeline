import os

# --- Security & Governance Settings ---
# Set to True to sanitize profiles and redact PII for LLM consumption.
# Set to False during development/debugging to retain raw mock data.
ENABLE_PII_MASKING: bool = True