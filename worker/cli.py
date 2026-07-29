"""CLI entrypoint for Portal BI worker jobs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path when invoked as python -m worker
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from worker.registry import get, list_jobs, load_builtin_jobs
from worker.runtime import JobContext, parse_business_date, setup_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="worker", description="Portal BI TMB — batch jobs")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Lista jobs registrados")

    run_p = sub.add_parser("run", help="Executa um job")
    run_p.add_argument("job_id", help="Identificador estável do job")
    run_p.add_argument("--force", action="store_true", help="Ignora idempotência")
    run_p.add_argument("--date", dest="business_date", help="Data de negócio YYYY-MM-DD")
    run_p.add_argument("--dry-run", action="store_true", help="Não envia e-mail")
    run_p.add_argument(
        "--if-due",
        action="store_true",
        help="Só executa se horário configurado já passou e ainda não houve sucesso no dia",
    )

    args = parser.parse_args(argv)
    logger = setup_logging()
    load_builtin_jobs()

    if args.command == "list":
        jobs = list_jobs()
        if not jobs:
            print("Nenhum job registrado.")
            return 0
        for job in jobs:
            print(f"{job.job_id}\t{job.description}")
        return 0

    if args.command == "run":
        spec = get(args.job_id)
        if spec is None:
            logger.error("Job desconhecido: %s", args.job_id)
            print(f"Job desconhecido: {args.job_id}", file=sys.stderr)
            return 2
        ctx = JobContext(
            job_id=spec.job_id,
            business_date=parse_business_date(args.business_date),
            force=bool(args.force),
            dry_run=bool(args.dry_run),
            if_due=bool(args.if_due),
            logger=logger,
        )
        logger.info(
            "start job=%s date=%s force=%s dry_run=%s if_due=%s",
            ctx.job_id,
            ctx.business_date,
            ctx.force,
            ctx.dry_run,
            ctx.if_due,
        )
        result = spec.run(ctx)
        logger.info(
            "end job=%s status=%s message=%s metrics=%s",
            ctx.job_id,
            result.status,
            result.message,
            result.metrics,
        )
        print(f"{result.status}: {result.message}")
        return 0 if result.status in {"success", "skipped"} else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
