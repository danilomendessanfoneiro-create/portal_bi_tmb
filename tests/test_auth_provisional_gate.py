"""US-012: provisional password login gate."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.models import User
from app.services.auth_service import AuthError, AuthService
from app.utils.password import hash_password


def test_authenticate_rejects_expired_provisional():
    pwd = "TempPassword1!"
    user = User(
        id=1,
        login="u",
        password_hash=hash_password(pwd),
        profile="filial",
        branch="SPO",
        display_name="U",
        name="U",
        code="u",
        must_change_password=True,
        temporary_password_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    repo = MagicMock()
    repo.get_by_login.return_value = user
    svc = AuthService(users=repo)
    with pytest.raises(AuthError, match="expirou"):
        svc.authenticate("u", pwd)


def test_authenticate_allows_valid_provisional():
    pwd = "TempPassword1!"
    user = User(
        id=1,
        login="u",
        password_hash=hash_password(pwd),
        profile="filial",
        branch="SPO",
        display_name="U",
        name="U",
        code="u",
        must_change_password=True,
        temporary_password_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    repo = MagicMock()
    repo.get_by_login.return_value = user
    svc = AuthService(users=repo)
    assert svc.authenticate("u", pwd).login == "u"
