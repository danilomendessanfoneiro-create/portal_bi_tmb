"""US-006: admin set password."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models import User
from app.services.user_service import UserService, UserServiceError


def _user(**kwargs) -> User:
    defaults = dict(
        id=2,
        login="filial1",
        password_hash="old",
        profile="filial",
        branch="SPO",
        display_name="F",
        name="F",
        code="filial1",
    )
    defaults.update(kwargs)
    return User(**defaults)


def test_set_password_admin_generate():
    repo = MagicMock()
    repo.get_by_id.return_value = _user()
    repo.update.return_value = _user(password_hash="new")
    svc = UserService(users=repo)
    user, plain = svc.set_password_admin(2, password=None, generate=True, actor="admin")
    assert user is not None
    assert plain is not None
    assert len(plain) >= 12
    fields = repo.update.call_args[0][1]
    assert "password_hash" in fields
    assert fields["must_change_password"] is False


def test_set_password_admin_rejects_weak():
    repo = MagicMock()
    repo.get_by_id.return_value = _user()
    svc = UserService(users=repo)
    with pytest.raises(UserServiceError, match="mínimo"):
        svc.set_password_admin(2, password="short", generate=False, actor="admin")
