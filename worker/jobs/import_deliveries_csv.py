"""
Job: import_deliveries_csv

Migra dados de dados/entregas_relatorio.csv para prb_deliveries (source=csv).
"""

from __future__ import annotations

from pathlib import Path

from app.services.csv_delivery_import_service import CsvDeliveryImportService
from worker.idempotency import begin_run, complete_run
from worker.registry import register
from worker.runtime import JobContext, JobResult


@register(
    "import_deliveries_csv",
    "Migra planilha CSV (dados/entregas_relatorio.csv) para prb_deliveries",
)
def run_csv(ctx: JobContext) -> JobResult:
    run_id = None
    if not ctx.dry_run:
        run_id, early = begin_run(ctx)
        if early is not None:
            return early

    try:
        csv_path = Path(ctx.csv_path) if getattr(ctx, "csv_path", None) else None
        replace = True if getattr(ctx, "replace_csv", None) is None else bool(ctx.replace_csv)
        result = CsvDeliveryImportService().run(
            csv_path=csv_path,
            replace=replace,
            dry_run=ctx.dry_run,
            actor="worker",
        )
        status = "success" if result.status == "success" else "failed"
        jr = JobResult(
            status=status,
            message=result.message,
            metrics={
                "inserted": result.rows_inserted,
                "updated": result.rows_updated,
                "deleted": result.rows_deleted,
                "read": result.rows_read,
                "dry_run": ctx.dry_run,
                "replace": replace,
            },
        )
        if ctx.dry_run:
            return jr
        return complete_run(run_id, jr)
    except Exception as exc:
        ctx.logger.exception("import_deliveries_csv failed")
        return complete_run(
            run_id,
            JobResult(status="failed", message=str(exc), metrics={"error": type(exc).__name__}),
        )
