"""Generates one mock loan-contract text file per customer already in the DuckDB
roster, parallel in shape to generate_data.py: it reads the existing customers
rather than inventing its own, and writes deterministic output so the dataset is
reproducible and diffable across runs.

Run from the repo root: python -m src.infra.database.generate_mock_documents

Seeding rule (a pure function of customer_id, never randomized per run):
    customer_id % 10 == 1  -> rate_above_cap    (interest rate above the 24% ceiling)
    customer_id % 10 == 2  -> missing_signature (borrower signature left unsigned)
    customer_id % 10 == 3  -> name_mismatch     (contract name differs from Borrower.full_name)
    anything else          -> clean             (no seeded issue)
Across the 100-customer roster this seeds 30 documents with an issue and leaves
70 clean, and re-running the script regenerates byte-for-byte identical output
for every customer_id.
"""

import random

from src.infra.config import DATA_DIR
from src.infra.database.database import get_read_connection

MOCK_DOCUMENTS_DIR = DATA_DIR / "mock_documents"

LEGAL_RATE_CAP = 24.00
TERM_OPTIONS = [24, 36, 48, 60]


def _issue_for(customer_id: int) -> str:
    remainder = customer_id % 10
    if remainder == 1:
        return "rate_above_cap"
    if remainder == 2:
        return "missing_signature"
    if remainder == 3:
        return "name_mismatch"
    return "clean"


def _mismatched_name(full_name: str, rng: random.Random) -> str:
    """Swaps the surname for a plausible one, so the whole document consistently
    names someone close to, but not exactly, the registered borrower - the case
    the deterministic name check (document_agent.check_name_mismatch) must catch.
    """
    parts = full_name.split()
    suffix = rng.choice(["Neto", "Junior", "Filho", "Souza", "Pereira"])
    return " ".join([*parts[:-1], suffix]) if len(parts) > 1 else f"{full_name} {suffix}"


def _render_contract(customer_id: int, full_name: str, loan_amount: float, issue: str) -> str:
    rng = random.Random(customer_id)  # seeded on customer_id alone: same output every run
    term_months = TERM_OPTIONS[customer_id % len(TERM_OPTIONS)]
    rate = rng.uniform(26.0, 38.0) if issue == "rate_above_cap" else rng.uniform(12.0, 22.0)
    contract_name = _mismatched_name(full_name, rng) if issue == "name_mismatch" else full_name
    signature_line = (
        "___________________________ (pending)"
        if issue == "missing_signature"
        else f"{contract_name} _______________________ (signed)"
    )

    return f"""CEDULA DE CREDITO BANCARIO (CCB) - LOAN AGREEMENT

Instrument No.: CCB-2026-{customer_id:05d}
Date of Execution: March {1 + customer_id % 28}, 2026

PARTIES
Lender: Meridian Capital Bank S.A.
Borrower: {contract_name}

LOAN TERMS
Principal Amount: R$ {loan_amount:,.2f}
Annual Interest Rate: {rate:.2f}% p.a.
Term: {term_months} months
Repayment: {term_months} equal monthly installments, first due 30 days after disbursement

GOVERNING LAW
Maximum permitted annual percentage rate for this credit class: {LEGAL_RATE_CAP:.2f}% p.a.
This agreement is not enforceable until signed by both parties.

SIGNATURES
Borrower: {signature_line}
Lender Representative: R. Matsuda _______________________ (signed)
"""


def generate_mock_documents() -> int:
    with get_read_connection() as conn:
        rows = conn.execute(
            "SELECT customer_id, full_name, loan_amount_requested FROM customers ORDER BY customer_id"
        ).fetchall()

    MOCK_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    for customer_id, full_name, loan_amount in rows:
        issue = _issue_for(customer_id)
        text = _render_contract(customer_id, full_name, float(loan_amount), issue)
        (MOCK_DOCUMENTS_DIR / f"contract_{customer_id}.txt").write_text(text)

    print(f"✓ Generated {len(rows)} mock loan documents in {MOCK_DOCUMENTS_DIR}")
    return len(rows)


if __name__ == "__main__":
    generate_mock_documents()
