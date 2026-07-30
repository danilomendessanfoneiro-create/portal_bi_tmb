"""API integration settings persistence (prb_api_settings)."""

from __future__ import annotations

from typing import Any, Optional

from app.models.settings_models import ApiSettings
from app.repositories.base import get_connection
from app.schemas.settings import ApiSettingsFilter

ALLOWED_SORT = {"name": "name", "created_on": "created_on", "id": "id"}


def _row(row: dict[str, Any]) -> ApiSettings:
    return ApiSettings(
        id=row["id"],
        name=row["name"],
        base_url=row["base_url"],
        endpoint=row["endpoint"],
        token_encrypted=row["token_encrypted"],
        timeout_seconds=int(row.get("timeout_seconds") or 60),
        page_size=int(row.get("page_size") or 500),
        initial_load_days=int(row.get("initial_load_days") or 90),
        is_default=bool(row.get("is_default", False)),
        created_by=row.get("created_by"),
        created_on=row.get("created_on"),
        modified_by=row.get("modified_by"),
        modified_on=row.get("modified_on"),
        enabled=bool(row.get("enabled", True)),
    )


class ApiSettingsRepository:
    def get_by_id(self, item_id: int, *, include_disabled: bool = False) -> Optional[ApiSettings]:
        sql = "SELECT * FROM prb_api_settings WHERE id = %s"
        params: list[Any] = [item_id]
        if not include_disabled:
            sql += " AND enabled = TRUE"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def get_default(self) -> Optional[ApiSettings]:
        sql = """
            SELECT * FROM prb_api_settings
            WHERE enabled = TRUE AND is_default = TRUE
            ORDER BY id ASC LIMIT 1
        """
        with get_connection() as conn:
            row = conn.execute(sql).fetchone()
        return _row(row) if row else None

    def clear_default(self, *, except_id: Optional[int] = None) -> None:
        sql = "UPDATE prb_api_settings SET is_default = FALSE WHERE is_default = TRUE"
        params: list[Any] = []
        if except_id is not None:
            sql += " AND id <> %s"
            params.append(except_id)
        with get_connection() as conn:
            conn.execute(sql, params)

    def list(self, filters: ApiSettingsFilter) -> tuple[list[ApiSettings], int]:
        where = ["1=1"]
        params: list[Any] = []
        if filters.enabled is True:
            where.append("enabled = TRUE")
        elif filters.enabled is False:
            where.append("enabled = FALSE")
        if filters.search:
            where.append("(name ILIKE %s OR base_url ILIKE %s OR endpoint ILIKE %s)")
            term = f"%{filters.search.strip()}%"
            params.extend([term, term, term])
        sort_col = ALLOWED_SORT.get(filters.sort_by, "name")
        sort_dir = "DESC" if filters.sort_dir.lower() == "desc" else "ASC"
        where_sql = " AND ".join(where)
        page = max(1, filters.page)
        page_size = max(1, min(100, filters.page_size))
        offset = (page - 1) * page_size
        with get_connection() as conn:
            total = int(conn.execute(f"SELECT COUNT(*) AS total FROM prb_api_settings WHERE {where_sql}", params).fetchone()["total"])
            rows = conn.execute(
                f"SELECT * FROM prb_api_settings WHERE {where_sql} ORDER BY {sort_col} {sort_dir} NULLS LAST LIMIT %s OFFSET %s",
                [*params, page_size, offset],
            ).fetchall()
        return [_row(r) for r in rows], total

    def insert(self, *, data: dict[str, Any], actor: str) -> ApiSettings:
        sql = """
            INSERT INTO prb_api_settings (
                name, base_url, endpoint, token_encrypted, timeout_seconds, page_size,
                initial_load_days, is_default, created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, NOW(), %s
            ) RETURNING *
        """
        with get_connection() as conn:
            row = conn.execute(
                sql,
                [
                    data["name"],
                    data["base_url"],
                    data["endpoint"],
                    data["token_encrypted"],
                    data["timeout_seconds"],
                    data["page_size"],
                    data["initial_load_days"],
                    data["is_default"],
                    actor,
                    actor,
                    data["enabled"],
                ],
            ).fetchone()
        return _row(row)

    def update(self, item_id: int, fields: dict[str, Any], actor: str) -> Optional[ApiSettings]:
        if not fields:
            return self.get_by_id(item_id, include_disabled=True)
        allowed = {
            "name",
            "base_url",
            "endpoint",
            "token_encrypted",
            "timeout_seconds",
            "page_size",
            "initial_load_days",
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
        sql = f"UPDATE prb_api_settings SET {', '.join(sets)} WHERE id = %s RETURNING *"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def soft_delete(self, item_id: int, actor: str) -> Optional[ApiSettings]:
        return self.update(item_id, {"enabled": False, "is_default": False}, actor)
