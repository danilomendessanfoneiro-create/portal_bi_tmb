"""Idempotency helpers for worker jobs."""

from __future__ import annotations

from datetime import date
from typing import Optional

from app.repositories.job_run_repository import JobRunRepository
from worker.runtime import JobContext, JobResult


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
    repo.finish(
        run_id,
        status=result.status,
        message=result.message,
        metrics=result.metrics,
        artifact_path=str(result.artifact_path) if result.artifact_path else None,
    )
    return result
