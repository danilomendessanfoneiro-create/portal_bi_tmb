"""report_overdue_daily — orquestra fases de e-mail de atraso.

Fases (automações em prb_job_settings, mesma janela `--if-due` / `--force`):

- ``report_branch_daily`` — filiais (`user.branch` = entrega.filial; e-mails em ``prb_users.report_emails``)
- ``report_client_daily`` — clientes (`prb_clients.cnpj` = entrega.`cnpj_cliente`; e-mails em ``prb_clients.emails``)
- ``report_managerial`` — destinatários gerenciais em ``prb_email_recipients``

Disparo manual (Admin → import / botão de e-mails) chama o job ``report_overdue_daily``
com ``--force``, executando todas as fases cuja automação esteja habilitada.
Agendamento: espelha filiais — seed ``report_client_daily`` (migration 036), horário
independente em Administração → Jobs. Layout HTML reutilizado via ``build_report_html``.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from limpeza import processar_entregas
from app.services.job_schedule_service import (
    AUTOMATION_BRANCH,
    AUTOMATION_CLIENT,
    AUTOMATION_MANAGERIAL,
    JobScheduleService,
)
from app.services.user_service import UserService
from app.utils.report_emails import parse_report_emails
from worker.adapters.mailer import (
    MailSendError,
    resolve_daily_mail,
    resolve_smtp_only,
    send_report_email,
)
from worker.adapters.report_html import build_report_html, build_report_subject
from worker.idempotency import begin_run, complete_run
from worker.runtime import JobContext, JobResult, TZ_SP

CSV_COLUMNS = [
    ("nro_entrega", "codigo_entrega"),
    ("nota_fiscal", "nota_fiscal"),
    ("cliente", "cliente"),
    ("filial", "filial"),
    ("prazo_considerado", "data_prevista"),
    ("data_referencia", "data_atual"),
    ("dias_atraso", "dias_atraso"),
    ("status", "status"),
    ("motorista", "transportadora_motorista"),
    ("cidade_entrega", "cidade_entrega"),
    ("uf_entrega", "uf_entrega"),
    ("valor_total", "valor_total"),
    ("motivo_atraso", "motivo_atraso"),
]

_DIGITS_RE = re.compile(r"\D+")


def _load_frames(csv_path: Path, business_date: date) -> tuple[pd.DataFrame, pd.DataFrame]:
    del csv_path  # fonte operacional = Postgres
    df = processar_entregas(data_referencia=business_date)
    overdue = df[df["atrasado"]].copy()
    due_today = df[df["vence_hoje"]].copy()
    for frame in (overdue, due_today):
        frame["data_referencia"] = business_date.isoformat()
        if "dias_atraso" in frame.columns:
            frame["dias_atraso"] = frame["dias_atraso"].fillna(0).astype(int)
    return overdue, due_today


def _write_csv(overdue: pd.DataFrame, out_path: Path) -> int:
    export = pd.DataFrame()
    for src, dest in CSV_COLUMNS:
        if src in overdue.columns:
            export[dest] = overdue[src]
        else:
            export[dest] = np.nan
    if "data_prevista" in export.columns:
        export["data_prevista"] = pd.to_datetime(export["data_prevista"], errors="coerce").dt.strftime(
            "%Y-%m-%d"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    export.to_csv(out_path, index=False, sep=";", encoding="utf-8-sig")
    return len(export)


def _filter_branch(df: pd.DataFrame, branch: str) -> pd.DataFrame:
    if df is None or df.empty:
        return df.iloc[0:0].copy() if df is not None else pd.DataFrame()
    return df[df["filial"].astype(str) == str(branch)].copy()


def _filter_cnpj(df: pd.DataFrame, cnpj: str) -> pd.DataFrame:
    """Filtra entregas cujo cnpj_cliente (só dígitos) casa com o CNPJ do cadastro."""
    if df is None or df.empty:
        return df.iloc[0:0].copy() if df is not None else pd.DataFrame()
    target = _DIGITS_RE.sub("", str(cnpj or ""))
    if not target:
        return df.iloc[0:0].copy()
    if "cnpj_cliente" not in df.columns:
        return df.iloc[0:0].copy()

    def _digits(value: object) -> str:
        if value is None:
            return ""
        try:
            if pd.isna(value):
                return ""
        except (TypeError, ValueError):
            pass
        return _DIGITS_RE.sub("", str(value))

    series = df["cnpj_cliente"].map(_digits)
    return df[series == target].copy()


def _phase_due(automation_id: str, ctx: JobContext) -> bool:
    if not ctx.if_due:
        return True
    return JobScheduleService().is_due(automation_id, now=datetime.now(TZ_SP))


def _begin_phase(ctx: JobContext, automation_id: str):
    phase_ctx = replace(ctx, job_id=automation_id)
    return begin_run(phase_ctx)


def _plain_fallback(audience: str) -> str:
    return (
        f"Olá, bom dia!\n\n{audience},\n\n"
        "Segue relatório de notas em atraso da sua filial.\n"
        "Peço que baixe os canhotos com urgência e para as notas que serão "
        "entregues em atraso favor retornar com a previsão.\n"
        "Abra este e-mail em um cliente que suporte HTML para ver as tabelas.\n"
    )


def _run_phase_branch(
    ctx: JobContext,
    overdue: pd.DataFrame,
    due_today: pd.DataFrame,
) -> dict:
    metrics: dict = {"phase": "branch", "sent": 0, "skipped_no_email": 0, "errors": []}
    if not _phase_due(AUTOMATION_BRANCH, ctx):
        metrics["skipped_schedule"] = True
        ctx.logger.info("Fase filiais fora da janela (--if-due)")
        return metrics

    run_id: int | None = None
    if not ctx.dry_run:
        run_id, early = _begin_phase(ctx, AUTOMATION_BRANCH)
        if early is not None:
            metrics["idempotent"] = True
            metrics["message"] = early.message
            return metrics

    try:
        users = UserService().list_filial_for_reports()
        smtp = None if ctx.dry_run else resolve_smtp_only()
        for user in users:
            branch = (user.branch or "").strip()
            emails = parse_report_emails(user.report_emails)
            if not emails:
                metrics["skipped_no_email"] += 1
                ctx.logger.warning("Filial %s (%s) sem e-mails — pulando", branch, user.login)
                continue
            br_overdue = _filter_branch(overdue, branch)
            br_due = _filter_branch(due_today, branch)
            subject = build_report_subject(branch)
            html = build_report_html(
                audience_name=branch,
                overdue=br_overdue,
                due_today=br_due,
            )
            if ctx.dry_run:
                metrics["sent"] += len(emails)
                ctx.logger.info(
                    "Dry-run filial %s → %s (atrasados=%s vence_hoje=%s)",
                    branch,
                    emails,
                    len(br_overdue),
                    len(br_due),
                )
                continue
            assert smtp is not None
            try:
                send_report_email(
                    config=smtp,
                    subject=subject,
                    body=_plain_fallback(branch),
                    html_body=html,
                    to_emails=emails,
                    attachment=None,
                )
                metrics["sent"] += len(emails)
                ctx.logger.info(
                    "Enviado filial %s → %s (atrasados=%s vence_hoje=%s)",
                    branch,
                    emails,
                    len(br_overdue),
                    len(br_due),
                )
            except Exception as exc:
                metrics["errors"].append({"branch": branch, "error": str(exc)})
                ctx.logger.exception("Falha envio filial %s", branch)

        if ctx.dry_run:
            return metrics
        status = "failed" if metrics["errors"] and metrics["sent"] == 0 else "success"
        msg = (
            f"Fase filiais: {metrics['sent']} envio(s), "
            f"{metrics['skipped_no_email']} sem e-mail, "
            f"{len(metrics['errors'])} erro(s)."
        )
        complete_run(
            run_id,
            JobResult(status=status, message=msg, metrics=metrics),
        )
        if status == "failed":
            raise MailSendError(msg)
        return metrics
    except Exception as exc:
        if not ctx.dry_run:
            complete_run(
                run_id,
                JobResult(status="failed", message=str(exc), metrics={**metrics, "error": type(exc).__name__}),
            )
        raise


def _run_phase_client(
    ctx: JobContext,
    overdue: pd.DataFrame,
    due_today: pd.DataFrame,
) -> dict:
    """Fase clientes: match CNPJ cadastro ↔ entrega.cnpj_cliente; mesmo HTML das filiais."""
    metrics: dict = {
        "phase": "client",
        "sent": 0,
        "skipped_no_email": 0,
        "skipped_no_cnpj": 0,
        "errors": [],
    }
    if not _phase_due(AUTOMATION_CLIENT, ctx):
        metrics["skipped_schedule"] = True
        ctx.logger.info("Fase clientes fora da janela (--if-due)")
        return metrics

    run_id: int | None = None
    if not ctx.dry_run:
        run_id, early = _begin_phase(ctx, AUTOMATION_CLIENT)
        if early is not None:
            metrics["idempotent"] = True
            metrics["message"] = early.message
            return metrics

    try:
        from app.services.client_service import ClientService

        try:
            clients = ClientService().list_for_reports()
        except Exception as exc:
            # US-008 (prb_clients) pode ainda não estar aplicada — não derruba o job.
            ctx.logger.warning("Fase clientes indisponível: %s", exc)
            metrics["unavailable"] = True
            metrics["message"] = str(exc)
            if not ctx.dry_run and run_id is not None:
                complete_run(
                    run_id,
                    JobResult(
                        status="success",
                        message=f"Fase clientes pulada: {exc}",
                        metrics=metrics,
                    ),
                )
            return metrics

        smtp = None if ctx.dry_run else resolve_smtp_only()
        for client in clients:
            cnpj = (client.cnpj or "").strip()
            digits = _DIGITS_RE.sub("", cnpj)
            if not digits:
                metrics["skipped_no_cnpj"] += 1
                ctx.logger.warning("Cliente %s sem CNPJ válido — pulando", client.name)
                continue
            emails = client.emails
            if not emails:
                metrics["skipped_no_email"] += 1
                ctx.logger.warning("Cliente %s (%s) sem e-mails — pulando", client.name, digits)
                continue
            cl_overdue = _filter_cnpj(overdue, digits)
            cl_due = _filter_cnpj(due_today, digits)
            audience = client.name
            subject = build_report_subject(audience)
            html = build_report_html(
                audience_name=audience,
                overdue=cl_overdue,
                due_today=cl_due,
            )
            if ctx.dry_run:
                metrics["sent"] += len(emails)
                ctx.logger.info(
                    "Dry-run cliente %s → %s (atrasados=%s vence_hoje=%s)",
                    audience,
                    emails,
                    len(cl_overdue),
                    len(cl_due),
                )
                continue
            assert smtp is not None
            try:
                send_report_email(
                    config=smtp,
                    subject=subject,
                    body=_plain_fallback(audience),
                    html_body=html,
                    to_emails=emails,
                    attachment=None,
                )
                metrics["sent"] += len(emails)
                ctx.logger.info(
                    "Enviado cliente %s → %s (atrasados=%s vence_hoje=%s)",
                    audience,
                    emails,
                    len(cl_overdue),
                    len(cl_due),
                )
            except Exception as exc:
                metrics["errors"].append({"client": audience, "cnpj": digits, "error": str(exc)})
                ctx.logger.exception("Falha envio cliente %s", audience)

        if ctx.dry_run:
            return metrics
        status = "failed" if metrics["errors"] and metrics["sent"] == 0 else "success"
        msg = (
            f"Fase clientes: {metrics['sent']} envio(s), "
            f"{metrics['skipped_no_email']} sem e-mail, "
            f"{metrics['skipped_no_cnpj']} sem CNPJ, "
            f"{len(metrics['errors'])} erro(s)."
        )
        complete_run(
            run_id,
            JobResult(status=status, message=msg, metrics=metrics),
        )
        if status == "failed":
            raise MailSendError(msg)
        return metrics
    except Exception as exc:
        if not ctx.dry_run:
            complete_run(
                run_id,
                JobResult(status="failed", message=str(exc), metrics={**metrics, "error": type(exc).__name__}),
            )
        raise


def _run_phase_managerial(
    ctx: JobContext,
    overdue: pd.DataFrame,
    due_today: pd.DataFrame,
) -> dict:
    metrics: dict = {"phase": "managerial", "sent": 0, "errors": []}
    if not _phase_due(AUTOMATION_MANAGERIAL, ctx):
        metrics["skipped_schedule"] = True
        ctx.logger.info("Fase gerencial fora da janela (--if-due)")
        return metrics

    sched = JobScheduleService().get(AUTOMATION_MANAGERIAL)
    freq = (sched.frequency if sched else "daily") or "daily"
    if freq in {"weekly", "monthly"}:
        msg = f"Geração {freq} não implementada nesta etapa."
        ctx.logger.info(msg)
        metrics["deferred"] = True
        metrics["message"] = msg
        return metrics

    run_id: int | None = None
    if not ctx.dry_run:
        run_id, early = _begin_phase(ctx, AUTOMATION_MANAGERIAL)
        if early is not None:
            metrics["idempotent"] = True
            metrics["message"] = early.message
            return metrics

    try:
        if ctx.dry_run:
            recipients = []
            try:
                mail = resolve_daily_mail()
                recipients = [r for r in mail.recipients if r.enabled]
            except MailSendError:
                ctx.logger.warning("Dry-run gerencial: SMTP/destinatários indisponíveis — simula 0 envios")
            for recip in recipients:
                name = (recip.name or recip.email).strip()
                metrics["sent"] += 1
                ctx.logger.info("Dry-run gerencial → %s (%s)", name, recip.email)
            return metrics

        mail = resolve_daily_mail()
        recipients = [r for r in mail.recipients if r.enabled]
        if not recipients:
            raise MailSendError("Nenhum destinatário diário ativo cadastrado.")

        for recip in recipients:
            name = (recip.name or recip.email).strip()
            subject = build_report_subject(name)
            html = build_report_html(
                audience_name=name,
                overdue=overdue,
                due_today=due_today,
            )
            try:
                send_report_email(
                    config=mail,
                    subject=subject,
                    body=_plain_fallback(name),
                    html_body=html,
                    to_emails=[recip.email],
                    attachment=None,
                )
                metrics["sent"] += 1
                ctx.logger.info("Enviado gerencial → %s <%s>", name, recip.email)
            except Exception as exc:
                metrics["errors"].append({"email": recip.email, "error": str(exc)})
                ctx.logger.exception("Falha envio gerencial %s", recip.email)

        status = "failed" if metrics["errors"] and metrics["sent"] == 0 else "success"
        msg = f"Fase gerencial: {metrics['sent']} envio(s), {len(metrics['errors'])} erro(s)."
        complete_run(run_id, JobResult(status=status, message=msg, metrics=metrics))
        if status == "failed":
            raise MailSendError(msg)
        return metrics
    except Exception as exc:
        if not ctx.dry_run:
            complete_run(
                run_id,
                JobResult(status="failed", message=str(exc), metrics={**metrics, "error": type(exc).__name__}),
            )
        raise


def execute(ctx: JobContext) -> JobResult:
    try:
        overdue, due_today = _load_frames(ctx.data_csv, ctx.business_date)
        out_path = ctx.reports_dir / "atrasos_consolidado.csv"
        rows = _write_csv(overdue, out_path)

        snapshot_metrics = {"status": "skipped", "message": "dry_run"}
        if not ctx.dry_run:
            from app.services.bi_snapshot_service import BiSnapshotService

            snap = BiSnapshotService().capture_if_absent(
                ctx.business_date,
                overdue,
                actor="worker",
                source="job",
                source_job_id=ctx.job_id,
            )
            snapshot_metrics = {
                "status": snap.status,
                "message": snap.message,
                "run_id": snap.run_id,
                "rows": snap.rows,
            }
            if snap.status == "failed":
                ctx.logger.error("Snapshot falhou (e-mail continua): %s", snap.message)
            else:
                ctx.logger.info("Snapshot: %s", snap.message)

        branch_metrics = _run_phase_branch(ctx, overdue, due_today)
        client_metrics = _run_phase_client(ctx, overdue, due_today)
        managerial_metrics = _run_phase_managerial(ctx, overdue, due_today)

        metrics = {
            "rows_overdue": rows,
            "rows_due_today": int(len(due_today)),
            "artifact": str(out_path),
            "snapshot": snapshot_metrics,
            "branch": branch_metrics,
            "client": client_metrics,
            "managerial": managerial_metrics,
        }
        msg = (
            f"Job concluído. Filiais sent={branch_metrics.get('sent', 0)}; "
            f"clientes sent={client_metrics.get('sent', 0)}; "
            f"gerencial sent={managerial_metrics.get('sent', 0)}; "
            f"snapshot={snapshot_metrics.get('status')}."
        )
        return JobResult(status="success", message=msg, metrics=metrics, artifact_path=out_path)
    except Exception as exc:
        ctx.logger.exception("report_overdue_daily failed")
        return JobResult(status="failed", message=str(exc), metrics={"error": type(exc).__name__})
