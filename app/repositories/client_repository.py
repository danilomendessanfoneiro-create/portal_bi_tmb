"""Clients persistence (prb_clients)."""

from __future__ import annotations

from typing import Any, Optional

from app.models.client import Client
from app.repositories.base import get_connection
from app.schemas.client import ClientFilter

ALLOWED_SORT = {
    "name": "name",
    "cnpj": "cnpj",
    "created_on": "created_on",
    "id": "id",
}


def _row(row: dict[str, Any]) -> Client:
    return Client(
        id=row["id"],
        name=row["name"],
        cnpj=row["cnpj"],
        emails=row.get("emails"),
        created_by=row.get("created_by"),
        created_on=row.get("created_on"),
        modified_by=row.get("modified_by"),
        modified_on=row.get("modified_on"),
        enabled=bool(row.get("enabled", True)),
    )


class ClientRepository:
    def get_by_id(self, item_id: int, *, include_disabled: bool = False) -> Optional[Client]:
        sql = "SELECT * FROM prb_clients WHERE id = %s"
        params: list[Any] = [item_id]
        if not include_disabled:
            sql += " AND enabled = TRUE"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def get_by_cnpj(self, cnpj: str, *, include_disabled: bool = True) -> Optional[Client]:
        sql = "SELECT * FROM prb_clients WHERE cnpj = %s"
        params: list[Any] = [cnpj]
        if not include_disabled:
            sql += " AND enabled = TRUE"
        sql += " ORDER BY enabled DESC, id ASC LIMIT 1"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def get_enabled_by_cnpj(self, cnpj: str, *, exclude_id: Optional[int] = None) -> Optional[Client]:
        sql = "SELECT * FROM prb_clients WHERE cnpj = %s AND enabled = TRUE"
        params: list[Any] = [cnpj]
        if exclude_id is not None:
            sql += " AND id <> %s"
            params.append(exclude_id)
        sql += " LIMIT 1"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def list_enabled(self) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, name, cnpj, emails
                FROM prb_clients
                WHERE enabled = TRUE
                ORDER BY name
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def list(self, filters: ClientFilter) -> tuple[list[Client], int]:
        where = ["1=1"]
        params: list[Any] = []
        if filters.enabled is True:
            where.append("enabled = TRUE")
        elif filters.enabled is False:
            where.append("enabled = FALSE")
        if filters.search:
            where.append("(name ILIKE %s OR cnpj ILIKE %s OR COALESCE(emails,'') ILIKE %s)")
            term = f"%{filters.search.strip()}%"
            params.extend([term, term, term])
        sort_col = ALLOWED_SORT.get(filters.sort_by, "name")
        sort_dir = "DESC" if filters.sort_dir.lower() == "desc" else "ASC"
        where_sql = " AND ".join(where)
        page = max(1, filters.page)
        page_size = max(1, min(100, filters.page_size))
        offset = (page - 1) * page_size
        with get_connection() as conn:
            total = int(
                conn.execute(
                    f"SELECT COUNT(*) AS total FROM prb_clients WHERE {where_sql}",
                    params,
                ).fetchone()["total"]
            )
            rows = conn.execute(
                f"SELECT * FROM prb_clients WHERE {where_sql} "
                f"ORDER BY {sort_col} {sort_dir} NULLS LAST LIMIT %s OFFSET %s",
                [*params, page_size, offset],
            ).fetchall()
        return [_row(r) for r in rows], total

    def insert(self, *, data: dict[str, Any], actor: str) -> Client:
        sql = """
            INSERT INTO prb_clients (
                name, cnpj, emails,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
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
                    data["cnpj"],
                    data.get("emails"),
                    actor,
                    actor,
                    data.get("enabled", True),
                ],
            ).fetchone()
        return _row(row)

    def update(self, item_id: int, fields: dict[str, Any], actor: str) -> Optional[Client]:
        if not fields:
            return self.get_by_id(item_id, include_disabled=True)
        allowed = {"name", "cnpj", "emails", "enabled"}
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
        sql = f"UPDATE prb_clients SET {', '.join(sets)} WHERE id = %s RETURNING *"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def soft_delete(self, item_id: int, actor: str) -> Optional[Client]:
        return self.update(item_id, {"enabled": False}, actor)

    def upsert_by_cnpj(self, *, name: str, cnpj: str, actor: str) -> tuple[Client, str]:
        existing = self.get_by_cnpj(cnpj, include_disabled=True)
        if existing is None:
            return (
                self.insert(
                    data={"name": name, "cnpj": cnpj, "emails": None, "enabled": True},
                    actor=actor,
                ),
                "inserted",
            )
        fields: dict[str, Any] = {"name": name, "enabled": True}
        updated = self.update(int(existing.id), fields, actor)
        assert updated is not None
        return updated, "updated"
