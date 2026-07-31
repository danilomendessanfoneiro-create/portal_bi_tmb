"""
Jobs: import_deliveries_initial / import_deliveries_daily

Importa entregas da API TMS Elite para prb_deliveries.
"""

from __future__ import annotations

from datetime import datetime

from app.services.delivery_import_service import DeliveryImportService
from app.services.job_schedule_service import JobScheduleService
from worker.idempotency import begin_run, complete_run
from worker.registry import register
from worker.runtime import JobContext, JobResult, TZ_SP


def _schedule_allows(job_id: str, ctx: JobContext) -> bool:
    if not ctx.if_due:
        return True
    return JobScheduleService().is_due(job_id, now=datetime.now(TZ_SP))


def _execute_mode(ctx: JobContext, *, mode: str) -> JobResult:
    job_id = ctx.job_id
    if ctx.if_due and not _schedule_allows(job_id, ctx):
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
        svc = DeliveryImportService()
        if mode == "initial":
            result = svc.run_initial(
                business_date=ctx.business_date,
                dry_run=ctx.dry_run,
                actor="worker",
                job_id=job_id,
                initial_load_days=ctx.initial_load_days,
                dataset_sync_id=run_id,
            )
        else:
            result = svc.run_daily(
                business_date=ctx.business_date,
                dry_run=ctx.dry_run,
                actor="worker",
                job_id=job_id,
                dataset_sync_id=run_id,
            )

        status = "success" if result.status in {"success", "partial"} else "failed"
        if ctx.dry_run:
            return JobResult(
                status="success",
                message=result.message,
                metrics={
                    "dry_run": True,
                    "pages": result.pages_processed,
                    "errors": result.error_count,
                    "filter_start": str(result.filter_start),
                    "filter_end": str(result.filter_end),
                },
            )

        jr = JobResult(
            status=status,
            message=result.message,
            metrics={
                "pages": result.pages_processed,
                "inserted": result.rows_inserted,
                "updated": result.rows_updated,
                "errors": result.error_count,
                "filter_start": str(result.filter_start),
                "filter_end": str(result.filter_end),
                "import_status": result.status,
            },
        )
        return complete_run(run_id, jr)
    except Exception as exc:
        ctx.logger.exception("%s failed", job_id)
        return complete_run(
            run_id,
            JobResult(status="failed", message=str(exc), metrics={"error": type(exc).__name__}),
        )


@register(
    "import_deliveries_initial",
    "Carga inicial de entregas via API TMS Elite (janela initial_load_days)",
)
def run_initial(ctx: JobContext) -> JobResult:
    return _execute_mode(ctx, mode="initial")


@register(
    "import_deliveries_daily",
    "Atualização diária de entregas via API TMS Elite (dataCadastro do dia)",
)
def run_daily(ctx: JobContext) -> JobResult:
    return _execute_mode(ctx, mode="daily")


@register(
    "import_deliveries",
    "Alias da atualização diária (API TMS Elite)",
)
def run_alias(ctx: JobContext) -> JobResult:
    # Mantém compatibilidade com docs antigas do stub
    from dataclasses import replace

    return _execute_mode(replace(ctx, job_id="import_deliveries_daily"), mode="daily")
