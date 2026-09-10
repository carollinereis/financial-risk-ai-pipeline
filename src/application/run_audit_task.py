"""Background-thread wrapper around RunRiskAuditUseCase, so POST /customers/{id}/audit can
return immediately while the 3-agent committee runs in a FastAPI BackgroundTasks worker
thread. The use case itself (src/application/run_risk_audit.py) is untouched - this module
only tracks task state in Postgres and logs credit_history/risk_score_history snapshots
around it. The risk-score log in particular is the only place a trend across audit runs
exists at all, since DuckDB's agent_evaluations deliberately keeps only the current run.
"""

from src.api.schemas import AuditResultResponse
from src.application.run_risk_audit import RunRiskAuditUseCase
from src.infra.database.database import fetch_customer_by_id
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
            decision=result.decision,
            risk_tier=result.risk_tier,
            qual_assessment=result.qual_assessment,
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
            task.error = str(exc)
