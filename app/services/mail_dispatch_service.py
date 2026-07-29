"""Facade for outbound mail using default SMTP + active recipients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models.settings_models import EmailRecipient, SmtpSettings
from app.services.email_recipient_service import EmailRecipientService
from app.services.smtp_service import SmtpSettingsService
from app.utils.secret_box import decrypt_secret


@dataclass
class MailRuntimeConfig:
    smtp: SmtpSettings
    password: str
    recipients: list[EmailRecipient]


class MailDispatchService:
    """Uses the default SMTP config for automatic report delivery."""

    def __init__(
        self,
        smtp: Optional[SmtpSettingsService] = None,
        recipients: Optional[EmailRecipientService] = None,
    ) -> None:
        self._smtp = smtp or SmtpSettingsService()
        self._recipients = recipients or EmailRecipientService()

    def resolve_for_report(self, period: str) -> Optional[MailRuntimeConfig]:
        smtp = self._smtp.get_default()
        if smtp is None:
            return None
        password = decrypt_secret(smtp.password_encrypted)
        recipients = self._recipients.list_for_report(period)
        return MailRuntimeConfig(smtp=smtp, password=password, recipients=recipients)

    def resolve_smtp(self) -> Optional[MailRuntimeConfig]:
        smtp = self._smtp.get_default()
        if smtp is None:
            return None
        password = decrypt_secret(smtp.password_encrypted)
        return MailRuntimeConfig(smtp=smtp, password=password, recipients=[])
