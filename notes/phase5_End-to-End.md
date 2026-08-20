## Overview

**Phase 5** integrates the domain entities, ML risk engine, underwriting policy rules, and multi-agent AI framework into a unified, interactive Streamlit Web Application (`app.py`). This phase completes the transition from backend execution pipelines to an end-to-end human-in-the-loop decision framework.

---

## Key Architectural Highlights

* **Domain-Driven Entity Mapping:** Unified database records (DuckDB PII and financial metrics) into strongly-typed `CustomerProfile` entities, ensuring consistency across quantitative and qualitative risk modules.
* **Deterministic Policy Engine:** Automated quantitative risk screening using `UnderwritingPolicy` rules (checking credit score thresholds, DTI ratios, and ML probability scores).
* **Multi-Agent Audit Committee:** Dynamic orchestration of qualitative risk evaluation and agentic audit reasoning based on real-time customer data inputs.
* **Interactive UI/UX:** Built with Streamlit to enable underwriters to select customer profiles, view live quantitative model predictions, and inspect multi-agent committee findings in real time.

## Pipeline Execution Flow

```text
[ DuckDB / Profile Selection ]
              │
              ▼
    [ CustomerProfile Entity ]
              │
    ┌─────────┴─────────┐
    ▼                   ▼
[ XGBoost Model ]   [ Policy Engine ]
    │                   │
    └─────────┬─────────┘
              ▼
    [ Quantitative Risk Score ]
              │
              ▼
   [ Multi-Agent Committee ]
              │
              ▼
 [ Interactive Streamlit Audit Dashboard ]
```

## Application Dashboard Screenshots

> Streamlit Dashboard displaying customer profiles, live ML risk predictions, policy rule evaluations, and multi-agent audit notes.

<details>
<summary><b>View Audit Screenshots: Customer 101 - Alice Smith (Decision: REJECTED)</b></summary>

<br>

#### 1. Profile Selection
[Customer 101 Overview](./images/101_img1.png)

#### 2. Executive Decision
[Customer 101 Executive Decision REJECTED](./images/101_exec_decision.png)

#### 3. Quantitative Assessment
[Customer 101 Quantitative Assessment](./images/101_quant.png)

#### 4. Qualitative Assessment
[Customer 101 Qualitative Assessment](./images/101_qual.png)

</details>

<br>

<details>
<summary><b>View Audit Screenshots: Customer 102 - Bob Jones (Decision: APPROVED)</b></summary>

<br>

#### 1. Profile Selection
[Customer 102 Overview](./images/102_img1.png)

#### 2. Executive Decision
[Customer 102 Executive Decision APPROVED](./images/102_exec_decision.png)

#### 3. Quantitative Assessment
[Customer 102 Quantitative Assessment](./images/102_quant.png)

#### 4. Qualitative Assessment
[Customer 102 Qualitative Assessment](./images/102_qual.png)

</details>