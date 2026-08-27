"""US-003: login email validation and uniqueness in UserService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models import User
from app.schemas import UserCreate, UserUpdate
from app.services.user_service import UserService, UserServiceError
from app.utils.login_email import validate_login_email


def test_validate_login_email_trim_and_case():
    assert validate_login_email("  Foo@Example.COM ") == "foo@example.com"
    assert validate_login_email("") is None
    assert validate_login_email(None) is None
    with pytest.raises(ValueError):
        validate_login_email("not-an-email")


def test_create_rejects_duplicate_login_email():
    repo = MagicMock()
    repo.get_by_login.return_value = None
    repo.get_by_login_email.return_value = User(
        id=9,
        login="other",
        password_hash="x",
        profile="filial",
        branch="SPO",
        display_name="O",
        name="O",
        code="other",
        login_email="a@b.com",
    )
    svc = UserService(users=repo)
    with pytest.raises(UserServiceError, match="e-mail de login"):
        svc.create(
            UserCreate(
                login="new",
                password="SecretPass1!",
                profile="filial",
                branch="SPO",
                login_email="A@B.com",
            ),
            actor="admin",
        )


def test_update_persists_normalized_login_email():
    repo = MagicMock()
    current = User(
        id=2,
        login="filial1",
        password_hash="x",
        profile="filial",
        branch="SPO",
        display_name="F",
        name="F",
        code="filial1",
    )
    repo.get_by_id.return_value = current
    repo.get_by_login_email.return_value = None
    updated = User(
        id=2,
        login="filial1",
        password_hash="x",
        profile="filial",
        branch="SPO",
        display_name="F",
        name="F",
        code="filial1",
        login_email="user@tmb.com",
    )
    repo.update.return_value = updated
    svc = UserService(users=repo)
    result = svc.update(2, UserUpdate(login_email="  User@TMB.com "), actor="admin")
    assert result.login_email == "user@tmb.com"
    args = repo.update.call_args
    assert args[0][1]["login_email"] == "user@tmb.com"
