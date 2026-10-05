"""Background-thread wrapper around RunDocumentExtractionUseCase, so
POST /customers/{id}/documents/extract can return immediately while the extraction
LLM call runs in a FastAPI BackgroundTasks worker thread. Mirrors run_audit_task.py's
shape, but writes to DocumentExtractionTask/DocumentExtraction instead of
AuditTask/CreditHistoryEntry, and never touches the committee's tables.
"""

import json

from src.api.schemas import DocumentExtractionResult, ExtractedEntities
from src.application.run_document_extraction import RunDocumentExtractionUseCase
from src.infra.database.postgres.models import DocumentExtraction, DocumentExtractionTask
from src.infra.database.postgres.session import get_session


def run_document_extraction_task(customer_id: int, task_id: str) -> None:
    with get_session() as session:
        task = session.get(DocumentExtractionTask, task_id)
        task.status = "PROCESSING"

    try:
        result = RunDocumentExtractionUseCase().execute(customer_id)
        fields = result["fields"]

        response = DocumentExtractionResult(
            customer_id=customer_id,
            document_name=result["document_name"],
            entities=ExtractedEntities(
                borrower_name=fields.borrower_name,
                loan_amount=fields.loan_amount,
                interest_rate=fields.interest_rate,
                term_months=fields.term_months,
                signature_present=fields.signature_present,
            ),
            risk_flags=fields.risk_flags,
            executive_summary=fields.executive_summary,
            review_status=result["review_status"],
            execution_time_ms=result["execution_time_ms"],
        )

        with get_session() as session:
            task = session.get(DocumentExtractionTask, task_id)
            task.status = "COMPLETED"
            task.result_json = response.model_dump_json()
            session.add(
                DocumentExtraction(
                    customer_id=customer_id,
                    document_name=result["document_name"],
                    borrower_name=fields.borrower_name,
                    loan_amount=fields.loan_amount,
                    interest_rate=fields.interest_rate,
                    term_months=fields.term_months,
                    signature_present=fields.signature_present,
                    risk_flags_json=json.dumps(fields.risk_flags),
                    executive_summary=fields.executive_summary,
                    review_status=result["review_status"],
                )
            )
    except Exception as exc:
        with get_session() as session:
            task = session.get(DocumentExtractionTask, task_id)
            task.status = "FAILED"
            task.error = _describe_failure(exc)


# Same rationale as run_audit_task._describe_failure: the Ollama client re-raises
# the raw socket/HTTP error, not a message an underwriter should have to decode.
def _describe_failure(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if (
        "connection refused" in lowered
        or "econnrefused" in lowered
        or "connect call failed" in lowered
    ):
        return "Couldn't reach the local model. Is Ollama running?"
    if "timeout" in lowered or "timed out" in lowered:
        return "The local model took too long to respond. Try again in a moment."
    return f"The extraction failed unexpectedly: {message}"
