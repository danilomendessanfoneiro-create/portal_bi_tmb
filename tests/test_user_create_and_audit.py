"""US-014/015: create with provisional + audit helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.schemas import UserCreate
from app.services.user_service import UserService, UserServiceError
from app.utils.access_audit import audit_access_event


def test_create_rejects_unknown_profile():
    svc = UserService(users=MagicMock())
    with pytest.raises(UserServiceError, match="admin' ou 'filial"):
        svc.create(
            UserCreate(
                login="x",
                password="ValidPass1!xx",
                profile="gestao_entregas",
                branch="SPO",
            ),
            actor="admin",
        )


def test_audit_access_event_no_secret(caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="portal_bi.access_audit"):
        audit_access_event("admin_set_password", actor="admin", target_user_id=1, detail="manual")
    assert "admin_set_password" in caplog.text
    assert "password=" not in caplog.text.lower() or "password_hash" not in caplog.text
