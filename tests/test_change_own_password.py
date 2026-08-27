"""US-007: change own password."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models import User
from app.services.user_service import UserService, UserServiceError
from app.utils.password import hash_password


def test_change_own_password_ok(monkeypatch):
    monkeypatch.setenv("PASSWORD_SALT", "test-salt")
    # re-import not needed if settings already loaded — hash with same util
    pwd_hash = hash_password("OldPassword1!")
    user = User(
        id=1,
        login="u1",
        password_hash=pwd_hash,
        profile="filial",
        branch="SPO",
        display_name="U",
        name="U",
        code="u1",
    )
    repo = MagicMock()
    repo.update.return_value = user
    svc = UserService(users=repo)
    svc.change_own_password(
        user,
        current_password="OldPassword1!",
        new_password="NewPassword1!",
        confirm_password="NewPassword1!",
    )
    assert repo.update.called


def test_change_own_password_wrong_current():
    user = User(
        id=1,
        login="u1",
        password_hash=hash_password("OldPassword1!"),
        profile="admin",
        branch=None,
        display_name="U",
        name="U",
        code="u1",
    )
    svc = UserService(users=MagicMock())
    with pytest.raises(UserServiceError, match="atual"):
        svc.change_own_password(
            user,
            current_password="WrongPassword1!",
            new_password="NewPassword1!",
            confirm_password="NewPassword1!",
        )
