"""Password recovery token persistence (prb_password_recovery)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.repositories.base import get_connection


def _row(row: dict[str, Any]) -> dict[str, Any]:
    return dict(row)


class PasswordRecoveryRepository:
    def revoke_pending_for_user(self, user_id: int) -> None:
        sql = """
            UPDATE prb_password_recovery
            SET status = 'Revoked', revoked_at = NOW()
            WHERE user_id = %s AND status = 'Pending'
        """
        with get_connection() as conn:
            conn.execute(sql, [user_id])

    def insert(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO prb_password_recovery (
                user_id, token_hash, created_at, expires_at, status
            ) VALUES (%s, %s, NOW(), %s, 'Pending')
            RETURNING *
        """
        with get_connection() as conn:
            row = conn.execute(sql, [user_id, token_hash, expires_at]).fetchone()
        return _row(row)

    def get_by_token_hash(self, token_hash: str) -> Optional[dict[str, Any]]:
        sql = "SELECT * FROM prb_password_recovery WHERE token_hash = %s"
        with get_connection() as conn:
            row = conn.execute(sql, [token_hash]).fetchone()
        return _row(row) if row else None

    def mark_used(self, recovery_id: int) -> None:
        sql = """
            UPDATE prb_password_recovery
            SET status = 'Used', used_at = NOW()
            WHERE id = %s
        """
        with get_connection() as conn:
            conn.execute(sql, [recovery_id])
