# Phase 2: Database Layer with SQL (DuckDB) & Data Generation

**Tools Used:** Python 3.11+, DuckDB (`duckdb` library), `Faker` (`pt_BR`, `en_US`), `pathlib`  
**Objective:** Build an embedded relational database to ingest structured financial profiles and qualitative notes, powered by dynamic synthetic data generation, CSV decoupled ingestion, and intentional financial edge cases.

---

## 1. Architectural Overview & Data Flow

To mirror modern enterprise data engineering practices, data generation is completely decoupled from database engine initialization:

```text
[ generate_data.py ] ──(Generates)──> [ data/customers.csv ]
                                              │
                                     (Queries directly)
                                              ▼
                                      [ database.py ] (DuckDB)
                                              │
                                     (Fetches Raw Record)
                                              ▼
                                      [ security.py ] (Sanitizer)
```

### Core Design Principles

* **Production Pipeline Parity:** Raw customer data originates from an independent data file (`customers.csv`), simulating real-world Enterprise ETL/ELT pipelines where data lands from external datalakes.
* **Separation of Concerns:** `generate_data.py` focuses purely on data synthesis, `database.py` manages querying, and `security.py` enforces privacy governance.
* **Engine Flexibility:** Decoupling the data source ensures the query engine or ML models can be upgraded or swapped without modifying how synthetic data is generated.

---

## 2. Dynamic Seeding & Edge Case Modeling

To simulate a realistic banking environment, the data generation pipeline (`src/generate_data.py`) creates a dynamic dataset using Faker and random with a fixed seed (`42`) for full reproducibility, exporting directly to `data/customers.csv`.

### Key Architectural Standards:

* *Modern Python Standards* `(pathlib)`: Used `pathlib.Path` across scripts instead of manual string concatenation for reliable cross-platform file path management.

* *Context Managers* (`with` blocks): Refactored database operations in `src/database.py` using context managers (`with get_db_connection() as conn:`) to guarantee safe connection cleanup and prevent resource leaks.

* *Synthetic Scaling* (`Faker`): Scaled the dataset to *100 customer profiles*, generating both quantitative credit metrics and qualitative textual account notes.

* *Deterministic Seeding:* Enforced fixed seeds (`Faker.seed(42), random.seed(42)`) so the generated synthetic dataset remains identical across any machine or environment.

### Hardcoded Strategic Edge Cases

To rigorously test downstream ML model predictions and LLM reasoning in later phases, four specific customer profiles were hand-crafted as deterministic anchor test cases:

| ID | Name | Financial Profile | Expected Pipeline Behavior |
| :--- | :--- | :--- | :--- |
| **101** | Alice Smith | High Income ($210k), Low Score (580) | Tests if ML catches debt mismanagement despite high earnings. |
| **102** | Bob Jones | Low Income ($32k), Excellent Score (820) | Tests capacity constraints vs. pristine credit behavior. |
| **103** | Carlos Silva | High-Risk Repeat Offender (Score 510, DTI 0.58) | Features multiple risk indicators. Tests LLM Agent's ability to evaluate severe risk logs. |
| **104** | Diana Prince | Pristine Customer (Score 790, DTI 0.10) | Baseline model performance test with minimal risk markers. |
---

## 3. Database Schema Design (`src/database.py`)

DuckDB initializes the relational storage file at `data/financial_risk.duckdb` by reading directly from `data/customers.csv` via standard SQL syntax.

### `customers` Table Schema

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `customer_id` | `INTEGER` (PK) | Unique identifier for each customer |
| `full_name` | `VARCHAR` | Customer full name (PII) |
| `email` | `VARCHAR` | Customer email address (PII) |
| `phone` | `VARCHAR` | Customer cellphone number (PII) |
| `cpf` | `VARCHAR` | Brazilian CPF registration number (PII) |
| `annual_income` | `DOUBLE` | Annual income in USD |
| `credit_score` | `INTEGER` | FICO credit score (300 - 850) |
| `debt_to_income_ratio` | `DOUBLE` | Monthly debt obligations / gross monthly income (DTI) |
| `delinquencies_2yrs` | `INTEGER` | Missed payment instances in the last 24 months |
| `loan_amount_requested`| `DOUBLE` | Target loan amount requested |
| `employment_length_years` | `INTEGER` | Years at current employer |
| `notes` | `TEXT` | Qualitative text logs recorded by bank staff (Unstructured PII) |

---

## 4. Why DuckDB for Financial Engineering?

* **Embedded & Zero-Server:** Operates locally inside the Python process without requiring an external server daemon (unlike PostgreSQL or MySQL).
* **OLAP Analytical Speed:** Optimized for columnar analysis and feature extraction fed directly into downstream models.
* **Direct CSV Ingestion:** Ingests CSVs natively using `read_csv_auto()` without manual row-by-row iteration or verbose schema definitions.

### DuckDB Initialization & Sample Query Execution

_Terminal verification showing DuckDB populating 100 records directly from `customers.csv` and querying record #101._

[Click here to view DuckDB Query Output](./images/duckdb_query_screenshot.png)

---

## 5. Centralized Configuration & Governance (`src/config.py`)

System flags are governed via a single configuration file (`src/config.py`):

```python
# System-wide Security Flag
# True  -> Compliance Mode (Anonymizes attributes & redacts text PII)
# False -> Development Mode (Retains raw mock data for debugging)

ENABLE_PII_MASKING: bool = True
```

## 6. Security & Privacy Layer ```(src/security.py)```

Compliance middleware acts as a gatekeeper between DuckDB and downstream LLMs/ML models.

### Core Sanitization Functions:

1. `sanitize_customer_profile():` Replaces structured identifiers `(full_name $\rightarrow$ ANON_USER_101, email $\rightarrow$ anon_user_101@masked-domain.com).`

2. ```redact_pii_from_text():``` Uses regex patterns to scrub CPFs ```(123.456.789-00)```, emails, Brazilian/International phone numbers, and context-aware full/first names from text notes.

## 7. Security & Privacy Layer Output Verification

The security layer intercepts raw DuckDB records and sanitizes both structured attributes and unstructured notes prior to downstream processing:

[Click here to view Security Sanitizer Output](./images/security_sanitization_screenshot.png)

* **Input Raw Data (DuckDB):** Shows unmasked `Alice Smith` with active email, CPF, and phone number in raw notes.

* **Output for LLM Agent:** Demonstrates structured anonymization (`ANON_USER_101`) alongside dynamic regex redaction (`[REDACTED NAME]`, `[REDACTED EMAIL]`, `[REDACTED CPF]`, `[REDACTED PHONE]`).

## 8. Repository Hygiene (`.gitignore`)

To ensure binary database files and dynamic datasets are excluded from version control, the following rules are enforced in `.gitignore:`

```
# Ignore generated data & DuckDB storage

data/*.csv
data/*.db
data/*.duckdb


# Python virtual environment

venv/
__pycache__/
*.pyc
```

