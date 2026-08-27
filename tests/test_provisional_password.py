"""US-011: admin provisional password."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.models import User
from app.services.user_service import UserService, UserServiceError


def test_send_provisional_requires_login_email():
    repo = MagicMock()
    repo.get_by_id.return_value = User(
        id=1,
        login="u",
        password_hash="x",
        profile="filial",
        branch="SPO",
        display_name="U",
        name="U",
        code="u",
        login_email=None,
    )
    svc = UserService(users=repo)
    with pytest.raises(UserServiceError, match="e-mail de login"):
        svc.send_provisional_password(1, actor="admin")


def test_send_provisional_sets_flags_and_mails():
    repo = MagicMock()
    user = User(
        id=1,
        login="u",
        password_hash="old",
        profile="filial",
        branch="SPO",
        display_name="U",
        name="U",
        code="u",
        login_email="u@tmb.com",
    )
    repo.get_by_id.return_value = user
    repo.update.return_value = user
    svc = UserService(users=repo)
    with patch("app.services.user_service.resolve_default_smtp") as smtp:
        with patch("app.services.user_service.send_plain_email") as send:
            smtp.return_value = object()
            svc.send_provisional_password(1, actor="admin")
    fields = repo.update.call_args[0][1]
    assert fields["must_change_password"] is True
    assert fields["temporary_password_expires_at"] is not None
    send.assert_called_once()
    assert send.call_args.kwargs["to_emails"] == ["u@tmb.com"]
    body = send.call_args.kwargs["body"].lower()
    assert "login" in body or "usuário" in body or "usuario" in body
    assert "u" in send.call_args.kwargs["body"]
