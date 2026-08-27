"""Password recovery request / token lifecycle + recovery e-mail."""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional
from urllib.parse import urlencode

from app.config import settings
from app.repositories import UserRepository
from app.repositories.password_recovery_repository import PasswordRecoveryRepository
from app.utils.access_audit import audit_access_event
from app.utils.login_email import validate_login_email
from app.utils.outbound_mail import OutboundMailError, resolve_default_smtp, send_plain_email
from app.utils.password import hash_password, validate_password_policy

logger = logging.getLogger(__name__)

RECOVERY_TTL_MINUTES = 30
GENERIC_MESSAGE = (
    "Se o e-mail informado estiver cadastrado, você receberá as instruções "
    "para recuperação de senha."
)
EXPIRED_MESSAGE = (
    "Este link de recuperação expirou. Solicite uma nova recuperação de senha."
)
INVALID_MESSAGE = "Este link de recuperação é inválido ou já foi utilizado."


@dataclass
class RecoveryRequestResult:
    message: str
    raw_token: Optional[str] = None
    user_id: Optional[int] = None
    login_email: Optional[str] = None
    mail_sent: bool = False


@dataclass
class TokenValidation:
    valid: bool
    message: str
    recovery_id: Optional[int] = None
    user_id: Optional[int] = None


def hash_recovery_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def build_reset_link(raw_token: str) -> str:
    base = (settings.admin_public_url or settings.public_origin).rstrip("/")
    return f"{base}/reset-password?{urlencode({'token': raw_token})}"


def build_recovery_email_bodies(
    *,
    display_name: str | None,
    login: str,
    reset_link: str,
) -> tuple[str, str]:
    name = (display_name or login or "usuário").strip() or "usuário"
    text = (
        f"Olá, {name}.\n\n"
        "Recebemos uma solicitação de recuperação de senha no Portal BI TMB Logística.\n\n"
        f"Usuário (login): {login}\n\n"
        "Para definir uma nova senha, acesse o link abaixo "
        f"(válido por {RECOVERY_TTL_MINUTES} minutos):\n"
        f"{reset_link}\n\n"
        "Se você não solicitou esta recuperação, ignore este e-mail.\n"
        "Por segurança, não compartilhe este link.\n"
    )
    html = (
        f"<p>Olá, <strong>{name}</strong>.</p>"
        "<p>Recebemos uma solicitação de recuperação de senha no "
        "<strong>Portal BI TMB Logística</strong>.</p>"
        f"<p><strong>Usuário (login):</strong> <code>{login}</code></p>"
        f"<p>Para definir uma nova senha, acesse o link abaixo "
        f"(válido por <strong>{RECOVERY_TTL_MINUTES} minutos</strong>):</p>"
        f'<p><a href="{reset_link}">{reset_link}</a></p>'
        "<p>Se você não solicitou esta recuperação, ignore este e-mail. "
        "Não compartilhe este link.</p>"
    )
    return text, html


class PasswordRecoveryService:
    def __init__(
        self,
        users: Optional[UserRepository] = None,
        recoveries: Optional[PasswordRecoveryRepository] = None,
        mail_sender: Optional[Callable[..., None]] = None,
        smtp_resolver: Optional[Callable[[], object]] = None,
    ) -> None:
        self._users = users or UserRepository()
        self._recoveries = recoveries or PasswordRecoveryRepository()
        self._mail_sender = mail_sender or send_plain_email
        self._smtp_resolver = smtp_resolver or resolve_default_smtp

    def request_reset(self, email: str | None) -> RecoveryRequestResult:
        try:
            normalized = validate_login_email(email)
        except ValueError:
            return RecoveryRequestResult(message=GENERIC_MESSAGE)

        if not normalized:
            return RecoveryRequestResult(message=GENERIC_MESSAGE)

        user = self._users.get_by_login_email(normalized, include_disabled=False)
        if user is None or user.id is None:
            return RecoveryRequestResult(message=GENERIC_MESSAGE)

        self._recoveries.revoke_pending_for_user(int(user.id))
        raw = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(minutes=RECOVERY_TTL_MINUTES)
        self._recoveries.insert(
            user_id=int(user.id),
            token_hash=hash_recovery_token(raw),
            expires_at=expires,
        )

        mail_sent = False
        try:
            config = self._smtp_resolver()
            link = build_reset_link(raw)
            text, html = build_recovery_email_bodies(
                display_name=user.display_name or user.name or user.login,
                login=user.login,
                reset_link=link,
            )
            self._mail_sender(
                config=config,
                subject="Portal BI — recuperação de senha",
                body=text,
                html_body=html,
                to_emails=[normalized],
            )
            mail_sent = True
        except OutboundMailError as exc:
            logger.warning("Recuperação: SMTP indisponível para %s: %s", normalized, exc)
        except Exception:
            logger.exception("Recuperação: falha ao enviar e-mail para %s", normalized)

        audit_access_event(
            "password_recovery_requested",
            target_user_id=int(user.id),
            detail="mail_sent" if mail_sent else "mail_failed_or_skipped",
        )
        return RecoveryRequestResult(
            message=GENERIC_MESSAGE,
            raw_token=raw,
            user_id=int(user.id),
            login_email=normalized,
            mail_sent=mail_sent,
        )

    def validate_token(self, raw_token: str | None) -> TokenValidation:
        if not raw_token or not str(raw_token).strip():
            return TokenValidation(valid=False, message=INVALID_MESSAGE)
        row = self._recoveries.get_by_token_hash(hash_recovery_token(raw_token.strip()))
        if row is None:
            return TokenValidation(valid=False, message=INVALID_MESSAGE)
        status = (row.get("status") or "").strip()
        if status != "Pending":
            return TokenValidation(valid=False, message=INVALID_MESSAGE)
        expires_at = row.get("expires_at")
        if expires_at is None:
            return TokenValidation(valid=False, message=INVALID_MESSAGE)
        if getattr(expires_at, "tzinfo", None) is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            return TokenValidation(valid=False, message=EXPIRED_MESSAGE)
        return TokenValidation(
            valid=True,
            message="OK",
            recovery_id=int(row["id"]),
            user_id=int(row["user_id"]),
        )

    def reset_password(
        self,
        *,
        raw_token: str,
        new_password: str,
        confirm_password: str,
    ) -> None:
        if new_password != confirm_password:
            raise ValueError("A confirmação não confere com a nova senha.")
        try:
            validate_password_policy(new_password)
        except ValueError:
            raise
        validation = self.validate_token(raw_token)
        if not validation.valid:
            raise ValueError(validation.message)
        assert validation.user_id is not None and validation.recovery_id is not None
        updated = self._users.update(
            validation.user_id,
            {
                "password_hash": hash_password(new_password),
                "must_change_password": False,
                "temporary_password_expires_at": None,
            },
            actor="password-recovery",
        )
        if updated is None:
            raise ValueError("Não foi possível atualizar a senha.")
        self._recoveries.mark_used(validation.recovery_id)
        audit_access_event(
            "password_recovery_completed",
            target_user_id=validation.user_id,
        )
