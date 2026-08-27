"""Send transactional e-mails via default operational SMTP."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import Optional, Sequence

from app.services.mail_dispatch_service import MailDispatchService, MailRuntimeConfig

logger = logging.getLogger(__name__)


class OutboundMailError(Exception):
    pass


def resolve_default_smtp() -> MailRuntimeConfig:
    cfg = MailDispatchService().resolve_smtp()
    if cfg is None:
        raise OutboundMailError("Nenhuma configuração SMTP padrão ativa.")
    return cfg


def send_plain_email(
    *,
    config: MailRuntimeConfig,
    subject: str,
    body: str,
    to_emails: Sequence[str],
    html_body: Optional[str] = None,
) -> None:
    if not to_emails:
        raise OutboundMailError("Nenhum destinatário informado.")

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
        return msg

    def _login_and_send(smtp: smtplib.SMTP) -> None:
        smtp.login(config.smtp.username, config.password)
        for addr in to_emails:
            smtp.send_message(_build(addr), from_addr=envelope_from, to_addrs=[addr])

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
