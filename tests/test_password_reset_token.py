"""US-010: reset password with recovery token."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.models import User
from app.services.password_recovery_service import (
    EXPIRED_MESSAGE,
    PasswordRecoveryService,
    hash_recovery_token,
)


def test_validate_token_expired():
    recoveries = MagicMock()
    recoveries.get_by_token_hash.return_value = {
        "id": 1,
        "user_id": 2,
        "status": "Pending",
        "expires_at": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    svc = PasswordRecoveryService(users=MagicMock(), recoveries=recoveries)
    result = svc.validate_token("tok")
    assert result.valid is False
    assert result.message == EXPIRED_MESSAGE


def test_reset_password_marks_used():
    raw = "good-token"
    recoveries = MagicMock()
    recoveries.get_by_token_hash.return_value = {
        "id": 9,
        "user_id": 2,
        "status": "Pending",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
        "token_hash": hash_recovery_token(raw),
    }
    users = MagicMock()
    users.update.return_value = User(
        id=2,
        login="u",
        password_hash="n",
        profile="filial",
        branch="SPO",
        display_name="U",
        name="U",
        code="u",
    )
    svc = PasswordRecoveryService(users=users, recoveries=recoveries)
    svc.reset_password(
        raw_token=raw,
        new_password="NewPassword1!",
        confirm_password="NewPassword1!",
    )
    users.update.assert_called_once()
    recoveries.mark_used.assert_called_once_with(9)


def test_reset_password_mismatch():
    svc = PasswordRecoveryService(users=MagicMock(), recoveries=MagicMock())
    with pytest.raises(ValueError, match="confirmação"):
        svc.reset_password(
            raw_token="x",
            new_password="NewPassword1!",
            confirm_password="OtherPassword1!",
        )
