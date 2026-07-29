# Phase 3: Machine Learning Model Training, Database Persistence & Security Guardrails

**Objective:** Train, evaluate, and persist machine learning risk models to evaluate credit applicant default probabilities, persist model outputs to embedded storage, and enforce strict PII masking and prompt injection sanitization prior to LLM reasoning ingestion.

---

## 1. Architectural Overview & Data Flow

Phase 3 establishes a modular machine learning and security pipeline. The architecture decouples model evaluation, persistence, and security controls following Domain-Driven Design (DDD) principles:

```text
[ data/customers.csv ] ──(Ingests)──> [ database.py ] (DuckDB)
                                             │
                                   (Loads Feature Vectors)
                                             │
                                             ▼
                                      [ train_model.py ]
                                 (Evaluates RF vs XGBoost)
                                             │
                                   (Persists Predictions)
                                             │
                                             ▼
[ security.py ] <──(Queries Records)── [ DuckDB Storage ]
  └─ Masked PII
  └─ Cleaned Notes
  ```

### Core Design Principles

* **Domain-Driven Context Isolation:** Data synthesis (`generate_data.py`), relational persistence (`database.py`), model lifecycle management (`train_model.py` / `credit_risk_model.py`), and compliance guardrails (`security.py`) operate as independent, bounded contexts.
* **Model Serialization & Persistence:** The optimal trained classifier is serialized as a binary artifact (`models/xgb_v1.joblib`), while prediction risk scores are updated in DuckDB tables using vectorized SQL operations.
* **Adversarial Resilience:** Text inputs (underwriter notes) are sanitized prior to downstream processing to mitigate prompt injection attacks against future LLM agent stages.

## 2. Financial Modeling Standards & FICO Baseline Parameters

The synthetic customer data follows standard industry guidelines inspired by FICO credit scores and banking underwriting standards:

* **Credit Score:** Ranges from 300 to 850 (FICO scale). Scores above 700 are considered low risk (prime), while scores below 600 represent subprime/high risk.
* **Debt-to-Income Ratio (DTI):** The percentage of a customer's monthly income that goes toward paying debts. Banks generally prefer a DTI below 0.36 (36%). Higher DTIs mean higher risk.
* **Delinquencies (2 Years):** Count of missed payments in the last 24 months.
* **Ground Truth Formula:** Ground truth probabilistic risk targets (`is_high_risk`) are assigned based on a weighted combination of financial leverage metrics, ensuring realistic default probability distributions.

## 3. Model Training, Stratified Cross-Validation & Performance Metrics

Two supervised learning algorithms—**Random Forest** and **XGBoost Classifier**—were trained and evaluated on 100 customer records using an 80/20 stratified train-test split, followed by 5-fold stratified cross-validation.

### Statistical Performance Summary

| Metric | Random Forest Classifier | XGBoost Classifier (Selected) |
| :--- | :--- | :--- |
| **ROC-AUC Score** | 0.9667 | **0.9733** |
| **Precision (High Risk)** | — | **1.00** |
| **Recall (High Risk)** | — | **0.80** |
| **F1-Score (High Risk)** | — | **0.89** |
| **Overall Accuracy** | — | **0.95** |
| **5-Fold Stratified CV (Mean)** | — | **0.9000** ($\pm 0.0764$) |

### Model Training & Evaluation Log Verification Output

_Terminal execution output showing model algorithm comparison (Random Forest vs XGBoost), classification performance metrics, and 5-fold stratified cross-validation results._

[Model Training & Evaluation Output](./images/model_evaluation_training_screenshot.png)

## 4. Anchor Test Profile Verification (Sanity Check)

To ensure model outputs align with financial logic, four deterministic anchor customer profiles were evaluated post-training:

| Customer ID | Name | Financial Profile (FICO / DTI) | Model Risk Score | Risk Prediction | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **101** | Alice Smith | Score: 580 (Subprime) \| DTI: 0.45 (High) | 0.86 | True (High Risk) | Verified (High risk correctly assigned) |
| **102** | Bob Jones | Score: 820 (Prime) \| DTI: 0.15 (Low) | 0.01 | False (Low Risk) | Verified (Low risk correctly assigned) |
| **103** | Carlos Silva | Score: 510 (Subprime) \| DTI: 0.58 (High) | 0.94 | True (High Risk) | Verified (High risk correctly assigned) |
| **104** | Diana Prince | Score: 790 (Prime) \| DTI: 0.10 (Low) | 0.01 | False (Low Risk) | Verified (Low risk correctly assigned) |

### Security & Sanitization Suite Verification Output

_Terminal verification showing PII redaction on anchor customer profiles (Test 1), prompt injection filtering on adversarial notes (Test 2), and handling of edge-case missing PII (Test 3)._

[Security & Sanitization Suite Output](./images/security_sanitization_screenshot.png)


## 5. Security Guardrails & PII Privacy Compliance

The security module (`src/security.py`) enforces data transformation and sanitization controls before customer records reach downstream LLM reasoning agents (Phase 4):

* **PII Masking Layer:** Standard structured customer attributes are masked (e.g., CPF: `***.456.789-**`, Email: `a***e.smith@example.com`, Phone: `+55 11 *****-4321`) to comply with privacy regulations.
* **Prompt Injection Defense:** Unstructured text fields (such as underwriter notes) pass through regex sanitization filters. This strips HTML script vectors, structural override syntax (`<, >, {, }`), and escape characters (`\`) to prevent adversarial prompt manipulation.


