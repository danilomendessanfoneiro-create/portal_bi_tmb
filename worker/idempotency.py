"""Idempotency helpers for worker jobs."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from app.repositories.job_run_repository import JobRunRepository
from worker.runtime import JobContext, JobResult

logger = logging.getLogger("worker")


def begin_run(ctx: JobContext, repo: Optional[JobRunRepository] = None) -> tuple[Optional[int], Optional[JobResult]]:
    """
    Returns (run_id, early_result).
    If early_result is set, caller should return it immediately (skipped).
    """
    repo = repo or JobRunRepository()
    if not ctx.force and repo.has_success(ctx.job_id, ctx.business_date):
        return None, JobResult(
            status="skipped",
            message=f"Já existe execução success para {ctx.job_id} em {ctx.business_date}.",
            metrics={"idempotent": True},
        )
    run_id = repo.start(job_id=ctx.job_id, business_date=ctx.business_date)
    return run_id, None


def complete_run(
    run_id: Optional[int],
    result: JobResult,
    repo: Optional[JobRunRepository] = None,
) -> JobResult:
    if run_id is None:
        return result
    repo = repo or JobRunRepository()
    row = repo.finish(
        run_id,
        status=result.status,
        message=result.message,
        metrics=result.metrics,
        artifact_path=str(result.artifact_path) if result.artifact_path else None,
    )
    try:
        from app.services.tech_monitor_service import notify_visible_robot_run

        if row:
            notify_visible_robot_run(
                job_id=str(row["job_id"]),
                status=result.status,
                business_date=row["business_date"],
                started_on=row.get("started_on"),
                finished_on=row.get("finished_on"),
                duration_ms=row.get("duration_ms"),
                metrics=result.metrics,
                message=result.message,
                error_step=row.get("error_step"),
                run_id=row.get("id"),
            )
    except Exception:
        logger.exception("monitoramento técnico falhou após job run_id=%s", run_id)
    return result
