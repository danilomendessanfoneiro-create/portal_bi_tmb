"""Send report e-mails via configured SMTP."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Optional, Sequence

from app.services.mail_dispatch_service import MailDispatchService, MailRuntimeConfig


class MailSendError(Exception):
    pass


def send_report_email(
    *,
    config: MailRuntimeConfig,
    subject: str,
    body: str,
    to_emails: Sequence[str],
    html_body: Optional[str] = None,
    attachment: Optional[Path] = None,
) -> None:
    """Envia um e-mail por destinatário (evita limite de To em provedores trial)."""
    if not to_emails:
        raise MailSendError("Nenhum destinatário informado.")
    if attachment is not None and not attachment.exists():
        raise MailSendError(f"Anexo não encontrado: {attachment}")

    data = attachment.read_bytes() if attachment is not None else None
    from_header = formataddr((config.smtp.sender_name, config.smtp.sender_email))
    envelope_from = (config.smtp.username or config.smtp.sender_email).strip()
    timeout = config.smtp.timeout_seconds or 30

    def _build(to_addr: str) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_header
        msg["To"] = to_addr
        msg["Reply-To"] = config.smtp.sender_email
        if html_body:
            msg.set_content(body or "Veja a versão HTML deste e-mail.")
            msg.add_alternative(html_body, subtype="html")
        else:
            msg.set_content(body)
        if data is not None and attachment is not None:
            msg.add_attachment(
                data,
                maintype="text",
                subtype="csv",
                filename=attachment.name,
            )
        return msg

    def _login_and_send(smtp: smtplib.SMTP) -> None:
        smtp.login(config.smtp.username, config.password)
        for addr in to_emails:
            built = _build(addr)
            smtp.send_message(built, from_addr=envelope_from, to_addrs=[addr])

    # Porta 465 = SSL implícito (SMTP_SSL). STARTTLS (587) usa SMTP + starttls.
    if int(config.smtp.port) == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            config.smtp.host, config.smtp.port, timeout=timeout, context=context
        ) as smtp:
            _login_and_send(smtp)
    elif config.smtp.use_tls:
        with smtplib.SMTP(config.smtp.host, config.smtp.port, timeout=timeout) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            _login_and_send(smtp)
    else:
        with smtplib.SMTP(config.smtp.host, config.smtp.port, timeout=timeout) as smtp:
            _login_and_send(smtp)


def resolve_daily_mail() -> MailRuntimeConfig:
    cfg = MailDispatchService().resolve_for_report("daily")
    if cfg is None:
        raise MailSendError("Nenhuma configuração SMTP padrão ativa.")
    return cfg


def resolve_smtp_only() -> MailRuntimeConfig:
    cfg = MailDispatchService().resolve_smtp()
    if cfg is None:
        raise MailSendError("Nenhuma configuração SMTP padrão ativa.")
    return cfg
