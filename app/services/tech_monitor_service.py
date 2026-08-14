"""SMTP técnico (env) e e-mail de monitoramento dos robôs visíveis."""

from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
from typing import Any, Optional
from zoneinfo import ZoneInfo

from app.services.job_schedule_service import VISIBLE_AUTOMATIONS

logger = logging.getLogger("tech_monitor")
TZ_SP = ZoneInfo("America/Sao_Paulo")

JOB_TITLES = {
    "fetch_tmselite_spreadsheet": "Importação de pedidos",
    "report_branch_daily": "Relatório das Filiais",
    "report_client_daily": "Relatório dos Clientes",
    "report_managerial": "Relatório Gerencial",
}


@dataclass(frozen=True)
class TechSmtpConfig:
    host: str
    port: int
    username: str
    password: str
    sender_email: str
    sender_name: str
    to_email: str


def load_tech_smtp() -> Optional[TechSmtpConfig]:
    password = (os.getenv("TECH_SMTP_PASSWORD") or "").strip()
    if not password:
        return None
    return TechSmtpConfig(
        host=(os.getenv("TECH_SMTP_HOST") or "smtp.gmail.com").strip(),
        port=int(os.getenv("TECH_SMTP_PORT") or "587"),
        username=(os.getenv("TECH_SMTP_USER") or "jeverson.abreu@gmail.com").strip(),
        password=password,
        sender_email=(os.getenv("TECH_SMTP_FROM") or "jeverson.abreu@gmail.com").strip(),
        sender_name=(os.getenv("TECH_SMTP_FROM_NAME") or "jeverson").strip(),
        to_email=(os.getenv("TECH_SMTP_TO") or "jeverson.abreu@gmail.com").strip(),
    )


def resolve_monitor_environment() -> str:
    """Rótulo do ambiente no e-mail técnico (APP_ENV / TECH_MONITOR_ENV / PUBLIC_ORIGIN)."""
    explicit = (os.getenv("APP_ENV") or os.getenv("TECH_MONITOR_ENV") or "").strip()
    if explicit:
        return explicit
    origin = (os.getenv("PUBLIC_ORIGIN") or "").strip().lower()
    if "localhost" in origin or "127.0.0.1" in origin:
        return "local"
    if origin:
        return "produção"
    return "desconhecido"


def _fmt_clock(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        local = value
        if value.tzinfo is not None:
            local = value.astimezone(TZ_SP)
        return local.strftime("%H:%M:%S")
    text = str(value)
    if len(text) >= 19:
        return text[11:19]
    return text[11:16] if len(text) >= 16 else text


def _fmt_duration(ms: Any) -> str:
    try:
        total = max(0, int(ms))
    except (TypeError, ValueError):
        return "—"
    seconds = total // 1000
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _first(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _append_metric(lines: list[str], label: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    lines.append(f"{label}: {value}")


def _format_error_details(metrics: dict[str, Any]) -> list[str]:
    raw = metrics.get("errors")
    if not isinstance(raw, list) or not raw:
        return []
    out: list[str] = []
    for item in raw[:10]:
        if isinstance(item, dict):
            part = item.get("error") or item.get("message") or item.get("detail") or str(item)
        else:
            part = str(item)
        part = part.strip()
        if part:
            out.append(f"  - {part}")
    if len(raw) > 10:
        out.append(f"  - … e mais {len(raw) - 10} erro(s)")
    return out


def build_monitor_email(
    *,
    job_id: str,
    status: str,
    business_date: date,
    started_on: Any = None,
    finished_on: Any = None,
    duration_ms: Any = None,
    metrics: Optional[dict[str, Any]] = None,
    message: str = "",
    error_step: Optional[str] = None,
    run_id: Any = None,
) -> tuple[str, str]:
    metrics = dict(metrics or {})
    failed = status == "failed"
    label = "FALHA" if failed else "SUCESSO"
    title = JOB_TITLES.get(job_id, job_id)
    date_label = business_date.strftime("%d/%m/%Y")
    environment = resolve_monitor_environment()
    env_tag = environment.upper()
    if failed:
        subject = (
            f"Portal BI [{env_tag}] – FALHA – Relatório de Execução das Automações – {date_label}"
        )
    else:
        subject = f"Portal BI [{env_tag}] – Relatório de Execução das Automações – {date_label}"
    overall = "ATENÇÃO – EXISTEM FALHAS" if failed else "SUCESSO"
    result_msg = (message or "").strip() or (
        "Falha na execução." if failed else "Execução concluída."
    )
    step = _first(error_step, metrics.get("step"), metrics.get("error_step"))
    reason = _first(message, metrics.get("error"), metrics.get("message"))
    if failed and not reason:
        reason = "Falha na execução (sem detalhe adicional)."

    lines = [
        "Bom dia,",
        "",
        "Segue o resumo da execução das automações do Portal BI.",
        "",
        "RESUMO",
        "",
        f"Ambiente: {environment}",
        f"Data: {date_label}",
        f"Robô: {title}",
        f"Identificador: {job_id}",
        "",
        "Automações planejadas: 1",
        "Automações executadas: 1",
        f"Execuções com sucesso: {0 if failed else 1}",
        f"Execuções com falha: {1 if failed else 0}",
        "",
        "Execução geral:",
        overall,
        "",
        "DETALHAMENTO",
        "",
        title,
        f"Status: {label}",
        f"Resultado: {result_msg}",
    ]
    _append_metric(lines, "Run ID", run_id)
    lines.extend(
        [
            f"Início: {_fmt_clock(started_on)}",
            f"Fim: {_fmt_clock(finished_on)}",
            f"Duração: {_fmt_duration(duration_ms)}",
        ]
    )

    _append_metric(lines, "Arquivo", metrics.get("file_name"))
    _append_metric(lines, "Tamanho (bytes)", metrics.get("file_size"))
    _append_metric(lines, "Lote", metrics.get("batch_id"))
    _append_metric(
        lines,
        "Registros processados",
        _first(metrics.get("total_rows"), metrics.get("rows_processed"), metrics.get("processed")),
    )
    _append_metric(lines, "Registros válidos", metrics.get("valid_rows"))
    _append_metric(lines, "Registros com erro de validação", metrics.get("error_rows"))
    _append_metric(lines, "Status da validação", metrics.get("validation_status"))
    _append_metric(lines, "Status da importação", metrics.get("import_status"))
    _append_metric(
        lines,
        "Registros inseridos",
        _first(metrics.get("rows_inserted"), metrics.get("inserted")),
    )
    _append_metric(
        lines,
        "Registros atualizados",
        _first(metrics.get("rows_updated"), metrics.get("updated")),
    )
    _append_metric(lines, "E-mails enviados", _first(metrics.get("sent"), metrics.get("emails_sent")))
    _append_metric(lines, "Destinatários sem e-mail", metrics.get("skipped_no_email"))
    _append_metric(lines, "Clientes sem CNPJ", metrics.get("skipped_no_cnpj"))

    mail_errors = metrics.get("email_errors")
    if mail_errors is None and isinstance(metrics.get("errors"), list):
        mail_errors = len(metrics["errors"])
    _append_metric(lines, "E-mails com erro", mail_errors)

    if failed:
        lines.append("")
        lines.append("MOTIVO DA FALHA")
        lines.append("")
        _append_metric(lines, "Etapa", step)
        lines.append(f"Motivo: {reason}")
        detail_lines = _format_error_details(metrics)
        if detail_lines:
            lines.append("Detalhes:")
            lines.extend(detail_lines)
        if metrics.get("partial") or (metrics.get("sent") and mail_errors):
            lines.append("Envio parcial: sim")
        if metrics.get("rollback"):
            lines.append("Rollback: sim")
        lines.append("Necessidade de reprocessamento: sim")

    lines.extend(["", "Atenciosamente,", "Portal BI"])
    return subject, "\n".join(lines)


def send_tech_email(subject: str, body: str, *, smtp: Optional[smtplib.SMTP] = None) -> None:
    cfg = load_tech_smtp()
    if cfg is None:
        logger.warning("SMTP técnico não configurado (TECH_SMTP_PASSWORD vazio); e-mail de monitoramento ignorado.")
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{cfg.sender_name} <{cfg.sender_email}>"
    msg["To"] = cfg.to_email
    msg.set_content(body)
    if smtp is not None:
        smtp.send_message(msg)
        return
    with smtplib.SMTP(cfg.host, cfg.port, timeout=30) as client:
        client.ehlo()
        client.starttls()
        client.ehlo()
        client.login(cfg.username, cfg.password)
        client.send_message(msg)


def notify_visible_robot_run(
    *,
    job_id: str,
    status: str,
    business_date: date,
    started_on: Any = None,
    finished_on: Any = None,
    duration_ms: Any = None,
    metrics: Optional[dict[str, Any]] = None,
    message: str = "",
    error_step: Optional[str] = None,
    run_id: Any = None,
) -> None:
    if job_id not in VISIBLE_AUTOMATIONS:
        return
    if status not in {"success", "failed"}:
        return
    subject, body = build_monitor_email(
        job_id=job_id,
        status=status,
        business_date=business_date,
        started_on=started_on,
        finished_on=finished_on,
        duration_ms=duration_ms,
        metrics=metrics,
        message=message,
        error_step=error_step,
        run_id=run_id,
    )
    try:
        send_tech_email(subject, body)
    except Exception:
        logger.exception("Falha ao enviar e-mail técnico de monitoramento job=%s", job_id)
