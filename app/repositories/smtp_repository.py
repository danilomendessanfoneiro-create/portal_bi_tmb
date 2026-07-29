"""SMTP settings persistence (prb_smtp_settings)."""

from __future__ import annotations

from typing import Any, Optional

from app.models.settings_models import SmtpSettings
from app.repositories.base import get_connection
from app.schemas.settings import SmtpFilter

ALLOWED_SORT = {
    "name": "name",
    "host": "host",
    "created_on": "created_on",
    "id": "id",
}


def _row(row: dict[str, Any]) -> SmtpSettings:
    return SmtpSettings(
        id=row["id"],
        name=row["name"],
        host=row["host"],
        port=int(row["port"]),
        username=row["username"],
        password_encrypted=row["password_encrypted"],
        use_tls=bool(row["use_tls"]),
        sender_email=row["sender_email"],
        sender_name=row["sender_name"],
        timeout_seconds=row.get("timeout_seconds"),
        is_default=bool(row.get("is_default", False)),
        created_by=row.get("created_by"),
        created_on=row.get("created_on"),
        modified_by=row.get("modified_by"),
        modified_on=row.get("modified_on"),
        enabled=bool(row.get("enabled", True)),
    )


class SmtpSettingsRepository:
    def get_by_id(self, item_id: int, *, include_disabled: bool = False) -> Optional[SmtpSettings]:
        sql = "SELECT * FROM prb_smtp_settings WHERE id = %s"
        params: list[Any] = [item_id]
        if not include_disabled:
            sql += " AND enabled = TRUE"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def get_default(self) -> Optional[SmtpSettings]:
        sql = """
            SELECT * FROM prb_smtp_settings
            WHERE enabled = TRUE AND is_default = TRUE
            ORDER BY id ASC LIMIT 1
        """
        with get_connection() as conn:
            row = conn.execute(sql).fetchone()
        return _row(row) if row else None

    def clear_default(self, *, except_id: Optional[int] = None) -> None:
        sql = "UPDATE prb_smtp_settings SET is_default = FALSE WHERE is_default = TRUE"
        params: list[Any] = []
        if except_id is not None:
            sql += " AND id <> %s"
            params.append(except_id)
        with get_connection() as conn:
            conn.execute(sql, params)

    def list(self, filters: SmtpFilter) -> tuple[list[SmtpSettings], int]:
        where = ["1=1"]
        params: list[Any] = []
        if filters.enabled is True:
            where.append("enabled = TRUE")
        elif filters.enabled is False:
            where.append("enabled = FALSE")
        if filters.search:
            where.append(
                "(name ILIKE %s OR host ILIKE %s OR sender_email ILIKE %s OR username ILIKE %s)"
            )
            term = f"%{filters.search.strip()}%"
            params.extend([term, term, term, term])
        sort_col = ALLOWED_SORT.get(filters.sort_by, "name")
        sort_dir = "DESC" if filters.sort_dir.lower() == "desc" else "ASC"
        where_sql = " AND ".join(where)
        page = max(1, filters.page)
        page_size = max(1, min(100, filters.page_size))
        offset = (page - 1) * page_size
        with get_connection() as conn:
            total = int(
                conn.execute(
                    f"SELECT COUNT(*) AS total FROM prb_smtp_settings WHERE {where_sql}",
                    params,
                ).fetchone()["total"]
            )
            rows = conn.execute(
                f"SELECT * FROM prb_smtp_settings WHERE {where_sql} "
                f"ORDER BY {sort_col} {sort_dir} NULLS LAST LIMIT %s OFFSET %s",
                [*params, page_size, offset],
            ).fetchall()
        return [_row(r) for r in rows], total

    def insert(self, *, data: dict[str, Any], actor: str) -> SmtpSettings:
        sql = """
            INSERT INTO prb_smtp_settings (
                name, host, port, username, password_encrypted, use_tls,
                sender_email, sender_name, timeout_seconds, is_default,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, NOW(), %s, NOW(), %s
            )
            RETURNING *
        """
        with get_connection() as conn:
            row = conn.execute(
                sql,
                [
                    data["name"],
                    data["host"],
                    data["port"],
                    data["username"],
                    data["password_encrypted"],
                    data["use_tls"],
                    data["sender_email"],
                    data["sender_name"],
                    data.get("timeout_seconds"),
                    data.get("is_default", False),
                    actor,
                    actor,
                    data.get("enabled", True),
                ],
            ).fetchone()
        return _row(row)

    def update(self, item_id: int, fields: dict[str, Any], actor: str) -> Optional[SmtpSettings]:
        if not fields:
            return self.get_by_id(item_id, include_disabled=True)
        allowed = {
            "name",
            "host",
            "port",
            "username",
            "password_encrypted",
            "use_tls",
            "sender_email",
            "sender_name",
            "timeout_seconds",
            "is_default",
            "enabled",
        }
        sets = []
        params: list[Any] = []
        for key, value in fields.items():
            if key in allowed:
                sets.append(f"{key} = %s")
                params.append(value)
        sets.append("modified_by = %s")
        params.append(actor)
        sets.append("modified_on = NOW()")
        params.append(item_id)
        sql = f"UPDATE prb_smtp_settings SET {', '.join(sets)} WHERE id = %s RETURNING *"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def soft_delete(self, item_id: int, actor: str) -> Optional[SmtpSettings]:
        return self.update(item_id, {"enabled": False, "is_default": False}, actor)
