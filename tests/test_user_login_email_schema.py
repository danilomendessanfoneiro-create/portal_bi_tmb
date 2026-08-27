"""US-001: migration + User model fields for login email / provisional password."""

from __future__ import annotations

from pathlib import Path

from app.models import User

_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "database"
    / "migrations"
    / "044_add_prb_users_login_email_and_password_flags.sql"
)


def test_migration_044_defines_login_email_and_password_flags():
    sql = _MIGRATION.read_text(encoding="utf-8")
    assert "login_email" in sql
    assert "must_change_password" in sql
    assert "temporary_password_expires_at" in sql
    assert "uq_prb_users_login_email_lower" in sql
    assert "TIMESTAMPTZ" in sql.upper() or "timestamptz" in sql


def test_user_model_defaults_for_new_password_fields():
    user = User(
        id=1,
        login="u1",
        password_hash="x",
        profile="filial",
        branch="SPO",
        display_name="U",
        name="U",
        code="u1",
    )
    assert user.login_email is None
    assert user.must_change_password is False
    assert user.temporary_password_expires_at is None
