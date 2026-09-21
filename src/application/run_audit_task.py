"""Background-thread wrapper around RunRiskAuditUseCase, so POST /customers/{id}/audit can
return immediately while the 3-agent committee runs in a FastAPI BackgroundTasks worker
thread. The use case itself (src/application/run_risk_audit.py) is untouched - this module
only tracks task state in Postgres and logs credit_history/risk_score_history snapshots
around it. The risk-score log in particular is the only place a trend across audit runs
exists at all, since DuckDB's agent_evaluations deliberately keeps only the current run.
"""

from src.api.schemas import AuditResultResponse
from src.application.run_risk_audit import RunRiskAuditUseCase
from src.domain.entities import extract_rationale
from src.infra.database.database import (
    CRO_DECISION_TO_VERDICT,
    QUAL_ASSESSMENT_TO_VERDICT,
    QUANT_STANDING_TO_VERDICT,
    fetch_customer_by_id,
)
from src.infra.database.postgres.models import AuditTask, CreditHistoryEntry, RiskScoreHistoryEntry
from src.infra.database.postgres.session import get_session


def run_audit_task(customer_id: int, task_id: str) -> None:
    with get_session() as session:
        task = session.get(AuditTask, task_id)
        task.status = "PROCESSING"

    try:
        result = RunRiskAuditUseCase().execute(customer_id)
        response = AuditResultResponse(
            customer_id=result.customer_id,
            quantitative_standing=result.quant_standing,
            xgb_risk_score=result.risk_score,
            cro_decision=result.cro_report,
            quant_analysis=result.quant_report,
            qual_analysis=result.qual_report,
            rationale=extract_rationale(result.cro_report),
            decision=result.decision,
            risk_tier=result.risk_tier,
            qual_assessment=result.qual_assessment,
            # Same mapping record_audit_results uses to persist each agent's vote,
            # so a fresh run's verdict badges match what a reload would show.
            quant_verdict=QUANT_STANDING_TO_VERDICT.get(result.quant_standing, "ALERT"),
            qual_verdict=QUAL_ASSESSMENT_TO_VERDICT.get(result.qual_assessment, "ALERT"),
            cro_verdict=CRO_DECISION_TO_VERDICT.get(result.decision, "ALERT"),
            quant_basis=result.quant_basis,
            qual_basis=result.qual_basis,
            cro_basis=result.cro_basis,
        )

        customer = fetch_customer_by_id(customer_id)

        with get_session() as session:
            task = session.get(AuditTask, task_id)
            task.status = "COMPLETED"
            task.result_json = response.model_dump_json()
            if customer:
                session.add(
                    CreditHistoryEntry(customer_id=customer_id, score=int(customer["credit_score"]))
                )
            session.add(RiskScoreHistoryEntry(customer_id=customer_id, score=result.risk_score))
    except Exception as exc:
        with get_session() as session:
            task = session.get(AuditTask, task_id)
            task.status = "FAILED"
            task.error = _describe_failure(exc)


# The Ollama client re-raises the raw socket/HTTP error (e.g. a bare
# "[Errno 61] Connection refused" or an httpx timeout), not a message an
# underwriter should have to decode. Sniffed by keyword rather than exception
# type, since that stays correct across langchain/ollama/httpx version bumps -
# any of them can be the one that actually raises. The real text is never
# dropped: an unrecognized failure still reports itself in full.
def _describe_failure(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if "connection refused" in lowered or "econnrefused" in lowered or "connect call failed" in lowered:
        return "Couldn't reach the local model. Is Ollama running?"
    if "timeout" in lowered or "timed out" in lowered:
        return "The local model took too long to respond. Try again in a moment."
    return f"The audit failed unexpectedly: {message}"
