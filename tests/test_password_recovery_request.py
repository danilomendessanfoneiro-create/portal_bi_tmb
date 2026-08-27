"""US-008: password recovery request (anti-enumeration)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.models import User
from app.services.password_recovery_service import (
    GENERIC_MESSAGE,
    PasswordRecoveryService,
)


def test_request_reset_same_message_when_missing():
    users = MagicMock()
    users.get_by_login_email.return_value = None
    recoveries = MagicMock()
    svc = PasswordRecoveryService(users=users, recoveries=recoveries)
    result = svc.request_reset("nobody@example.com")
    assert result.message == GENERIC_MESSAGE
    assert result.raw_token is None
    recoveries.insert.assert_not_called()


def test_request_reset_creates_token_and_revokes_prior():
    users = MagicMock()
    users.get_by_login_email.return_value = User(
        id=5,
        login="u",
        password_hash="x",
        profile="filial",
        branch="SPO",
        display_name="U",
        name="U",
        code="u",
        login_email="u@example.com",
    )
    recoveries = MagicMock()
    svc = PasswordRecoveryService(users=users, recoveries=recoveries)
    result = svc.request_reset("  U@Example.com ")
    assert result.message == GENERIC_MESSAGE
    assert result.raw_token
    recoveries.revoke_pending_for_user.assert_called_once_with(5)
    recoveries.insert.assert_called_once()
    kwargs = recoveries.insert.call_args.kwargs
    assert kwargs["user_id"] == 5
    assert kwargs["token_hash"]
