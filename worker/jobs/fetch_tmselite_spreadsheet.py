"""Job: fetch_tmselite_spreadsheet — coleta RPA + upload manual existente."""

from __future__ import annotations

from datetime import datetime

from app.services.job_schedule_service import AUTOMATION_TMS_SPREADSHEET, JobScheduleService
from app.services.tms_spreadsheet_fetch_service import (
    TmsSpreadsheetFetchError,
    TmsSpreadsheetFetchService,
)
from worker.idempotency import begin_run, complete_run
from worker.registry import register
from worker.runtime import JobContext, JobResult, TZ_SP


@register(
    AUTOMATION_TMS_SPREADSHEET,
    "Coleta da planilha TMS Elite (Total → Ver Entregas → Excel) e importação no fluxo manual",
)
def run(ctx: JobContext) -> JobResult:
    if ctx.if_due and not JobScheduleService().is_due(AUTOMATION_TMS_SPREADSHEET, now=datetime.now(TZ_SP)):
        return JobResult(
            status="skipped",
            message="Fora da janela horária configurada (--if-due).",
            metrics={"if_due": True},
        )

    run_id = None
    if not ctx.dry_run:
        run_id, early = begin_run(ctx)
        if early is not None:
            return early

    try:
        metrics = TmsSpreadsheetFetchService().run(dry_run=ctx.dry_run)
        message = (
            f"Arquivo {metrics.get('file_name')} baixado (dry-run)."
            if ctx.dry_run
            else (
                f"Importado lote #{metrics.get('batch_id')} "
                f"({metrics.get('total_rows')} linhas) de {metrics.get('file_name')}."
            )
        )
        return complete_run(
            run_id,
            JobResult(status="success", message=message, metrics=metrics),
        )
    except TmsSpreadsheetFetchError as exc:
        ctx.logger.exception("coleta TMS falhou step=%s", exc.step)
        metrics = {"step": exc.step, **exc.extra}
        return complete_run(
            run_id,
            JobResult(status="failed", message=str(exc), metrics=metrics),
        )
    except Exception as exc:
        ctx.logger.exception("coleta TMS falhou")
        return complete_run(
            run_id,
            JobResult(status="failed", message=str(exc), metrics={"step": "unexpected"}),
        )
