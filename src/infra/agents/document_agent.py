"""Standalone entity-extraction agent for mock loan documents.

Independent of the 3-agent committee in agents.py: a different LLM call for a
different job (structured extraction, not free-form risk analysis), and its
output never feeds the committee's decision hierarchy in either direction.
"""

import json
import time

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, ValidationError

# Same local-model pattern as agents.py: deterministic, timeout-bound so a hung
# Ollama can't block the request indefinitely. format="json" makes Ollama emit
# parseable JSON instead of the label-line prose the committee agents produce -
# this is extraction, not analysis, so there is no report to read structure from.
LLM_TIMEOUT_SECONDS = 30.0
llm = ChatOllama(
    model="llama3.1",
    temperature=0.0,
    timeout=LLM_TIMEOUT_SECONDS,
    num_ctx=8192,
    repeat_penalty=1.1,
    format="json",
)

extraction_prompt = ChatPromptTemplate.from_template("""
You are a document analyst extracting structured data from a loan contract. Read
ONLY the document text below and invent nothing beyond it.

Document:
{document_text}

Return a single JSON object with exactly these keys:
- "borrower_name": string or null - the borrower's full name as it appears in the document
- "loan_amount": number or null - the principal loan amount
- "interest_rate": number or null - the annual interest rate, as a percentage (e.g. 12.5)
- "term_months": integer or null - the loan term in months
- "signature_present": boolean - true only if the borrower's signature block is signed
- "risk_flags": array of short strings - concrete issues found in the text (e.g. a rate
  above a cap stated elsewhere in the same document, a missing signature, a borrower
  name that differs between sections). Empty array if none.
- "executive_summary": string - 3 to 5 sentences summarizing the document and any
  flagged risks

Respond with ONLY the JSON object, no other text.
""")

extraction_agent = extraction_prompt | llm


class ExtractedFields(BaseModel):
    """Validates the LLM's raw JSON. Every field is optional or has a safe default,
    so a document with no signature line still validates cleanly - it just reports
    signature_present=False rather than failing.
    """

    borrower_name: str | None = None
    loan_amount: float | None = None
    interest_rate: float | None = None
    term_months: int | None = None
    signature_present: bool = False
    risk_flags: list[str] = []
    executive_summary: str = ""


def extract_document_entities(sanitized_text: str, document_name: str) -> dict:
    """Runs the extraction LLM call against already-sanitized document text.

    Fails closed on a malformed response: review_status is set to NEEDS_REVIEW and
    whatever fields did parse are kept, matching the project's existing fallback
    pattern (FALLBACK_BEHAVIORAL_ASSESSMENT in src/domain/entities.py) rather than
    guessing at fields the model didn't actually return.
    """
    started = time.perf_counter()
    response = extraction_agent.invoke({"document_text": sanitized_text})
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    fields, review_status = _parse_response(response.content)

    return {
        "document_name": document_name,
        "fields": fields,
        "review_status": review_status,
        "execution_time_ms": elapsed_ms,
    }


def _parse_response(content: str) -> tuple[ExtractedFields, str]:
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        return ExtractedFields(), "NEEDS_REVIEW"

    if not isinstance(raw, dict):
        return ExtractedFields(), "NEEDS_REVIEW"

    try:
        return ExtractedFields.model_validate(raw), "OK"
    except ValidationError:
        return _salvage_fields(raw), "NEEDS_REVIEW"


def check_name_mismatch(extracted_name: str | None, registered_name: str) -> bool:
    """Deterministic identity check, resolved in code rather than left to the LLM's
    own judgment - same reasoning as describe_xgb_band/describe_credit_bracket in
    agents.py resolving a comparison in Python instead of asking the model to grade
    itself.

    Case-folded and whitespace-stripped before comparing, so capitalization or
    incidental spacing alone never produces a false mismatch. A missing extracted
    name is not a mismatch - there is nothing to compare, so nothing is asserted.
    """
    if not extracted_name:
        return False
    return extracted_name.strip().casefold() != registered_name.strip().casefold()


def _salvage_fields(raw: dict) -> ExtractedFields:
    """Keeps only the keys that validate on their own, so one bad field (e.g. an
    interest_rate the model returned as a sentence) doesn't discard a perfectly
    good borrower_name next to it.
    """
    salvaged = {}
    for key in ExtractedFields.model_fields:
        if key not in raw:
            continue
        try:
            salvaged[key] = getattr(ExtractedFields.model_validate({key: raw[key]}), key)
        except ValidationError:
            continue
    return ExtractedFields.model_construct(**salvaged)
