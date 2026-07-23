# Phase 2: Database Layer with SQL (DuckDB)

**Tools Used:** Python 3.11+, DuckDB (`duckdb` library), `Faker`, `pathlib`  
**Objective:** Build an embedded relational SQL database to store structured customer financial profiles and unstructured qualitative account logs, powered by dynamic synthetic data generation and intentional financial edge cases.

---

## 1. Why DuckDB for Financial Engineering?

* **Embedded Architecture:** Runs directly inside the Python process without requiring a standalone server (e.g., PostgreSQL/MySQL server setup).
* **OLAP (Online Analytical Processing) Optimization:** Fast analytical processing over structured tables, making it ideal for feature extraction fed into Machine Learning models.
* **Standard SQL Syntax:** Uses universal relational database syntax (`CREATE TABLE`, `INSERT`, `SELECT`, `WHERE`, `FOREIGN KEY`, `LEFT JOIN`).

---

## 2. Database Schema Design

The database logic is implemented in **`src/database.py`**, which automatically initializes and seeds the database file located at **`data/financial_risk.db`**.

Two relational tables were created inside `data/financial_risk.db`:

### `customers` Table (Quantitative Features)
Stores numerical metrics used by our Classic ML model to evaluate credit default probability.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `customer_id` | `INTEGER` (PK) | Unique identifier for each customer |
| `full_name` | `VARCHAR` | Customer name |
| `annual_income` | `DOUBLE` | Annual income in USD |
| `credit_score` | `INTEGER` | FICO credit score (350 - 850) |
| `debt_to_income_ratio` | `DOUBLE` | Monthly debt obligations / monthly gross income (DTI) |
| `delinquencies_2yrs` | `INTEGER` | Missed payment instances in last 24 months |
| `loan_amount_requested`| `DOUBLE` | Target loan amount requested |
| `employment_length_years` | `INTEGER` | Years at current employer |

### `account_logs` Table (Qualitative Text Data)
Stores unstructured notes written by bank staff. This table will be queried by our **LLM Agents** in Phase 4 to extract contextual insights.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `log_id` | `INTEGER` (PK) | Unique log entry identifier |
| `customer_id` | `INTEGER` (FK) | Reference link to `customers.customer_id` |
| `log_date` | `DATE` | Date entry was recorded |
| `category` | `VARCHAR` | Category (Support, Collections, Risk Alert, Underwriting, Wealth Management) |
| `notes` | `TEXT` | Qualitative textual notes |

---

## 3. Dynamic Seeding & Edge Case Modeling

To simulate a realistic banking environment, the seeding script (`src/database.py`) was upgraded to generate dynamic datasets using `Faker` and `random` with a fixed seed (`42`) for full reproducibility.

### Key Architectural Upgrades:
1. **Modern Python Standards (`pathlib`):** Used `pathlib.Path` instead of string manipulations for cross-platform file path management.
2. **Context Managers (`with` blocks):** Refactored database connections using context managers (`with duckdb.connect(...)`) to ensure safe connection handling and automatic closing/committing.
3. **Synthetic Scaling (`Faker`):** Scaled dataset to **50 customer profiles** and dynamically generated associated unstructured account logs across categories.
4. **Relational Aggregations (`LEFT JOIN` & `GROUP BY`):** Built verification queries using `LEFT JOIN` to correctly count log records per customer without dropping customers who have zero logs.
5. **Foreign Key Handling:** Structured table re-creation in `src/database.py` starting with dependent tables first (`account_logs` before `customers`) to ensure clean execution resets without foreign key dependency errors.

### Hardcoded Strategic Edge Cases:
To rigorously test downstream ML model predictions and LLM reasoning, four specific customer profiles were hand-crafted:

| ID | Name | Financial Profile | Expected Pipeline Behavior |
| :--- | :--- | :--- | :--- |
| **101** | Alice Smith | High Income ($210k), Low Score (580) | Tests if ML catches debt mismanagement despite high earnings. |
| **102** | Bob Jones | Low Income ($32k), Excellent Score (820) | Tests capacity constraints vs. pristine credit behavior. |
| **103** | Carlos Silva | High-Risk Repeat Offender (Score 510, DTI 0.58) | Features **5 distinct historical log entries**. Tests LLM Agent's ability to summarize multi-event timelines. |
| **104** | Diana Prince | Pristine Customer (Score 790, DTI 0.10) | Features **0 account logs**. Tests LLM Agent grace handling when no qualitative text exists. |

---

## 4. SQL Verification Query

The relational database schema was verified using a SQL aggregation query with a `LEFT JOIN`:

```sql
SELECT 
    c.customer_id, 
    c.full_name, 
    c.annual_income, 
    c.credit_score, 
    COUNT(a.log_id) AS total_logs
FROM customers c
LEFT JOIN account_logs a ON c.customer_id = a.customer_id
WHERE c.customer_id IN (101, 102, 103, 104)
GROUP BY c.customer_id, c.full_name, c.annual_income, c.credit_score
ORDER BY c.customer_id;
```

### Expected Query Output:

| ID | Name | Income | Score | Total Logs |
| :--- | :--- | :--- | :--- | :--- |
| 101 | Alice Smith | $210,000 | 580 | 1 |
| 102 | Bob Jones | $32,000 | 820 | 1 |
| 103 | Carlos Silva | $45,000 | 510 | 5 |
| 104 | Diana Prince | $115,000 | 790 | 0 |



## 5. Security & Data Privacy Layer (`src/security.py`)

In production financial systems, AI components must comply with strict data privacy regulations (e.g., LGPD / GDPR) to prevent leakage of Personally Identifiable Information (PII) to downstream processing pipelines or external APIs.

---

### Key Architectural Features

1. **Local Privacy Enforcement:** Running models locally via Ollama guarantees that customer data remains within the local network perimeter and is never transmitted over the internet or logged by external API providers.

2. **Feature Flag Governance (`ENABLE_PII_MASKING`):**
   * **Development Mode (`False`):** Retains human-readable mock data (`Alice Smith`) for effortless local debugging, database inspection, and clear visual demos.
   * **Production / Compliance Mode (`True`):** Intercepts data right before feature engineering and LLM consumption to enforce strict automated PII scrubbing.

3. **Structured Attribute Masking (`sanitize_customer_profile`):** Replaces sensitive identifiers (such as customer full names) with deterministic, anonymous reference tokens (`ANON_USER_101`).

4. **Dynamic Unstructured Text Redaction (`redact_pii_from_text`):** 
   * Uses regular expressions (`re`) to scrub emails, phone numbers, and Brazilian CPFs.
   * **Context-Aware Name Redaction:** Dynamically strips full names (*"Alice Smith"*) and standalone first names (*"Alice"*) from qualitative bank notes using case-insensitive boundary regex and `re.escape()`.

---

### Verification & Visual Inspection

The security layer was tested against both operational states to verify data integrity and redaction accuracy:

#### 1. Development Mode (`ENABLE_PII_MASKING = False`)
*Maintains raw mock data for local testing and visualization.*

[Click to view Security Layer - Unmasked Output](./images/unsmasked_screenshot.png)

#### 2. Compliance Mode (`ENABLE_PII_MASKING = True`)
*Scrubs all sensitive metadata before passing logs to the LLM agent.*

[Click to view Security Layer - Masked Output](./images/masked_screenshot.png)

