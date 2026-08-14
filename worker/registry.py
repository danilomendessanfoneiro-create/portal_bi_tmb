"""Job registry — register and resolve batch jobs by stable id."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from worker.runtime import JobContext, JobResult

JobFn = Callable[[JobContext], JobResult]


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    description: str
    run: JobFn


_REGISTRY: dict[str, JobSpec] = {}


def register(job_id: str, description: str) -> Callable[[JobFn], JobFn]:
    def decorator(fn: JobFn) -> JobFn:
        if job_id in _REGISTRY:
            raise ValueError(f"Job já registrado: {job_id}")
        _REGISTRY[job_id] = JobSpec(job_id=job_id, description=description, run=fn)
        return fn

    return decorator


def get(job_id: str) -> Optional[JobSpec]:
    return _REGISTRY.get(job_id)


def list_jobs() -> list[JobSpec]:
    return sorted(_REGISTRY.values(), key=lambda j: j.job_id)


def load_builtin_jobs() -> None:
    """Import job modules so @register side effects run."""
    from worker.jobs import fetch_tmselite_spreadsheet as _fetch_tms  # noqa: F401
    from worker.jobs import import_deliveries as _imp  # noqa: F401
    from worker.jobs import import_deliveries_csv as _imp_csv  # noqa: F401
    from worker.jobs import report_overdue_daily as _rep  # noqa: F401
