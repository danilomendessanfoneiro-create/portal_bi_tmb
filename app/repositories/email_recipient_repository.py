"""Email recipients persistence (prb_email_recipients)."""

from __future__ import annotations

from typing import Any, Optional

from app.models.settings_models import EmailRecipient
from app.repositories.base import get_connection
from app.schemas.settings import RecipientFilter

ALLOWED_SORT = {
    "name": "name",
    "email": "email",
    "department": "department",
    "created_on": "created_on",
    "id": "id",
}


def _row(row: dict[str, Any]) -> EmailRecipient:
    return EmailRecipient(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        role_title=row.get("role_title"),
        department=row.get("department"),
        receive_daily=bool(row.get("receive_daily", True)),
        receive_weekly=bool(row.get("receive_weekly", False)),
        receive_monthly=bool(row.get("receive_monthly", False)),
        created_by=row.get("created_by"),
        created_on=row.get("created_on"),
        modified_by=row.get("modified_by"),
        modified_on=row.get("modified_on"),
        enabled=bool(row.get("enabled", True)),
    )


class EmailRecipientRepository:
    def get_by_id(self, item_id: int, *, include_disabled: bool = False) -> Optional[EmailRecipient]:
        sql = "SELECT * FROM prb_email_recipients WHERE id = %s"
        params: list[Any] = [item_id]
        if not include_disabled:
            sql += " AND enabled = TRUE"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def get_by_email(self, email: str, *, include_disabled: bool = True) -> Optional[EmailRecipient]:
        sql = "SELECT * FROM prb_email_recipients WHERE lower(email) = lower(%s)"
        params: list[Any] = [email]
        if not include_disabled:
            sql += " AND enabled = TRUE"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def list(self, filters: RecipientFilter) -> tuple[list[EmailRecipient], int]:
        where = ["1=1"]
        params: list[Any] = []
        if filters.enabled is True:
            where.append("enabled = TRUE")
        elif filters.enabled is False:
            where.append("enabled = FALSE")
        if filters.search:
            where.append(
                "(name ILIKE %s OR email ILIKE %s OR COALESCE(role_title,'') ILIKE %s "
                "OR COALESCE(department,'') ILIKE %s)"
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
                    f"SELECT COUNT(*) AS total FROM prb_email_recipients WHERE {where_sql}",
                    params,
                ).fetchone()["total"]
            )
            rows = conn.execute(
                f"SELECT * FROM prb_email_recipients WHERE {where_sql} "
                f"ORDER BY {sort_col} {sort_dir} NULLS LAST LIMIT %s OFFSET %s",
                [*params, page_size, offset],
            ).fetchall()
        return [_row(r) for r in rows], total

    def list_active_for_report(self, period: str) -> list[EmailRecipient]:
        col = {
            "daily": "receive_daily",
            "weekly": "receive_weekly",
            "monthly": "receive_monthly",
        }.get(period)
        if not col:
            return []
        sql = f"SELECT * FROM prb_email_recipients WHERE enabled = TRUE AND {col} = TRUE ORDER BY email"
        with get_connection() as conn:
            rows = conn.execute(sql).fetchall()
        return [_row(r) for r in rows]

    def insert(self, *, data: dict[str, Any], actor: str) -> EmailRecipient:
        sql = """
            INSERT INTO prb_email_recipients (
                name, email, role_title, department,
                receive_daily, receive_weekly, receive_monthly,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, NOW(), %s, NOW(), %s
            )
            RETURNING *
        """
        with get_connection() as conn:
            row = conn.execute(
                sql,
                [
                    data["name"],
                    data["email"],
                    data.get("role_title"),
                    data.get("department"),
                    data.get("receive_daily", True),
                    data.get("receive_weekly", False),
                    data.get("receive_monthly", False),
                    actor,
                    actor,
                    data.get("enabled", True),
                ],
            ).fetchone()
        return _row(row)

    def update(self, item_id: int, fields: dict[str, Any], actor: str) -> Optional[EmailRecipient]:
        if not fields:
            return self.get_by_id(item_id, include_disabled=True)
        allowed = {
            "name",
            "email",
            "role_title",
            "department",
            "receive_daily",
            "receive_weekly",
            "receive_monthly",
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
        sql = f"UPDATE prb_email_recipients SET {', '.join(sets)} WHERE id = %s RETURNING *"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def soft_delete(self, item_id: int, actor: str) -> Optional[EmailRecipient]:
        return self.update(item_id, {"enabled": False}, actor)
