"""
Job stub: import_deliveries

Futuro: consumir API de terceiros e persistir em prb_deliveries.
Nesta fase: no-op documentado — não chama API nem grava entregas.
"""

from __future__ import annotations

from worker.registry import register
from worker.runtime import JobContext, JobResult


@register(
    "import_deliveries",
    "STUB — importação diária de entregas (API futura; no-op nesta fase)",
)
def run(ctx: JobContext) -> JobResult:
    ctx.logger.info(
        "import_deliveries stub: nenhuma ação. Fonte temporária do BI permanece o CSV."
    )
    return JobResult(
        status="skipped",
        message="Stub: importação via API não implementada nesta fase.",
        metrics={"implemented": False},
    )
