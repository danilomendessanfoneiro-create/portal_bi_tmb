"""US-002: password recovery token table migration."""

from __future__ import annotations

from pathlib import Path

_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "database"
    / "migrations"
    / "045_create_prb_password_recovery.sql"
)


def test_migration_045_password_recovery_table():
    sql = _MIGRATION.read_text(encoding="utf-8")
    assert "prb_password_recovery" in sql
    assert "token_hash" in sql
    assert "user_id" in sql
    assert "expires_at" in sql
    assert "used_at" in sql
    assert "revoked_at" in sql
    for status in ("Pending", "Used", "Expired", "Revoked"):
        assert status in sql
    assert "ix_prb_password_recovery_active" in sql
