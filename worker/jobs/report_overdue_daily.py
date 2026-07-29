"""
Job: report_overdue_daily

Gera CSV consolidado de atrasos e envia um e-mail aos destinatários diários.
Implementação completa nas US-003/004; skeleton registra o job.
"""

from __future__ import annotations

from worker.registry import register
from worker.runtime import JobContext, JobResult


@register(
    "report_overdue_daily",
    "Relatório diário consolidado de entregas em atraso (CSV + e-mail)",
)
def run(ctx: JobContext) -> JobResult:
    from worker.jobs import report_overdue_daily_impl as impl

    return impl.execute(ctx)
