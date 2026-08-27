"""US-009: recovery e-mail content and send via default SMTP."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.models import User
from app.services.password_recovery_service import (
    GENERIC_MESSAGE,
    PasswordRecoveryService,
    RECOVERY_TTL_MINUTES,
    build_recovery_email_bodies,
    build_reset_link,
)


def test_build_reset_link_contains_token():
    link = build_reset_link("abcTOKEN")
    assert "reset-password" in link
    assert "token=abcTOKEN" in link


def test_recovery_email_body_has_expiry_and_no_password():
    text, html = build_recovery_email_bodies(
        display_name="Ana",
        login="ana",
        reset_link="https://example/reset-password?token=xyz",
    )
    assert "Portal BI" in text or "TMB" in text
    assert "Usuário (login): ana" in text
    assert "ana" in html
    assert str(RECOVERY_TTL_MINUTES) in text
    assert "https://example/reset-password?token=xyz" in text
    assert "senha atual" not in text.lower()
    assert "xyz" in html


def test_request_reset_sends_mail_via_default_smtp():
    users = MagicMock()
    users.get_by_login_email.return_value = User(
        id=3,
        login="ana",
        password_hash="x",
        profile="filial",
        branch="SPO",
        display_name="Ana",
        name="Ana",
        code="ana",
        login_email="ana@tmb.com",
    )
    recoveries = MagicMock()
    mail = MagicMock()
    smtp_cfg = object()
    svc = PasswordRecoveryService(
        users=users,
        recoveries=recoveries,
        mail_sender=mail,
        smtp_resolver=lambda: smtp_cfg,
    )
    result = svc.request_reset("ana@tmb.com")
    assert result.message == GENERIC_MESSAGE
    assert result.mail_sent is True
    mail.assert_called_once()
    kwargs = mail.call_args.kwargs
    assert kwargs["config"] is smtp_cfg
    assert kwargs["to_emails"] == ["ana@tmb.com"]
    assert "senha" in kwargs["subject"].lower()
    assert "reset-password" in kwargs["body"]
    assert "Usuário (login): ana" in kwargs["body"] or "login): ana" in kwargs["body"]
    assert "TECH_SMTP" not in kwargs["body"]
