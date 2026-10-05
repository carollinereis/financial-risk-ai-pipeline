"""Use case for one-shot entity extraction from a customer's own mock loan
document. Mirrors run_risk_audit.py's shape but is fully independent: no ML
score, no 3-agent committee, and it never touches loan_applications or
agent_evaluations.
"""

from src.infra.agents.document_agent import check_name_mismatch, extract_document_entities
from src.infra.config import DATA_DIR
from src.infra.database.postgres.models import Borrower
from src.infra.database.postgres.session import get_session
from src.infra.security.security import sanitize_input

MOCK_DOCUMENTS_DIR = DATA_DIR / "mock_documents"


class DocumentNotFoundError(Exception):
    pass


def mock_document_path(customer_id: int):
    """The one mock document generate_mock_documents.py produced for this
    customer, following its contract_{customer_id}.txt naming convention.
    """
    return MOCK_DOCUMENTS_DIR / f"contract_{customer_id}.txt"


class RunDocumentExtractionUseCase:
    """Loads a customer's own mock document, sanitizes it, runs it through the
    extraction agent, and flags a deterministic identity mismatch against the
    registered borrower record.
    """

    def execute(self, customer_id: int) -> dict:
        document_path = mock_document_path(customer_id)
        if not document_path.is_file():
            raise DocumentNotFoundError(f"No mock document generated for customer {customer_id}.")

        raw_text = document_path.read_text()
        sanitized_text = sanitize_input(raw_text)

        result = extract_document_entities(sanitized_text, document_path.name)
        fields = result["fields"]

        with get_session() as session:
            borrower = session.get(Borrower, customer_id)
        # Only asserted when a registered borrower actually exists to compare
        # against - an unregistered customer_id has nothing to mismatch.
        if borrower and check_name_mismatch(fields.borrower_name, borrower.full_name):
            fields.risk_flags = [*fields.risk_flags, "name_mismatch"]

        return result
