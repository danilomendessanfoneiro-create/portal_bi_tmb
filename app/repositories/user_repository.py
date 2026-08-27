"""User persistence (prb_users). Audit is handled by DB triggers."""

from __future__ import annotations

from typing import Any, Optional

from app.models import User
from app.repositories.base import get_connection
from app.schemas import UserFilter


ALLOWED_SORT = {
    "login": "login",
    "display_name": "display_name",
    "branch": "branch",
    "profile": "profile",
    "created_on": "created_on",
    "id": "id",
}


def _row_to_user(row: dict[str, Any]) -> User:
    return User(
        id=row["id"],
        login=row["login"],
        password_hash=row["password_hash"],
        profile=row["profile"],
        branch=row.get("branch"),
        display_name=row.get("display_name"),
        name=row.get("name"),
        code=row.get("code"),
        report_emails=row.get("report_emails"),
        login_email=row.get("login_email"),
        must_change_password=bool(row.get("must_change_password", False)),
        temporary_password_expires_at=row.get("temporary_password_expires_at"),
        created_by=row.get("created_by"),
        created_on=row.get("created_on"),
        modified_by=row.get("modified_by"),
        modified_on=row.get("modified_on"),
        enabled=bool(row.get("enabled", True)),
    )


class UserRepository:
    def get_by_id(self, user_id: int, *, include_disabled: bool = False) -> Optional[User]:
        sql = "SELECT * FROM prb_users WHERE id = %s"
        params: list[Any] = [user_id]
        if not include_disabled:
            sql += " AND enabled = TRUE"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row_to_user(row) if row else None

    def get_by_login(self, login: str, *, include_disabled: bool = False) -> Optional[User]:
        sql = "SELECT * FROM prb_users WHERE lower(login) = lower(%s)"
        params: list[Any] = [login]
        if not include_disabled:
            sql += " AND enabled = TRUE"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row_to_user(row) if row else None

    def get_by_login_email(self, email: str, *, include_disabled: bool = False) -> Optional[User]:
        sql = "SELECT * FROM prb_users WHERE login_email IS NOT NULL AND lower(login_email) = lower(%s)"
        params: list[Any] = [email]
        if not include_disabled:
            sql += " AND enabled = TRUE"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row_to_user(row) if row else None

    def list(self, filters: UserFilter) -> tuple[list[User], int]:
        where = ["1=1"]
        params: list[Any] = []

        # enabled=True → só ativos; False → só inativos; None → todos
        if filters.enabled is True:
            where.append("enabled = TRUE")
        elif filters.enabled is False:
            where.append("enabled = FALSE")

        if filters.profile:
            where.append("profile = %s")
            params.append(filters.profile)

        if filters.search:
            where.append(
                "(login ILIKE %s OR COALESCE(display_name,'') ILIKE %s "
                "OR COALESCE(branch,'') ILIKE %s OR COALESCE(name,'') ILIKE %s "
                "OR COALESCE(code,'') ILIKE %s)"
            )
            term = f"%{filters.search.strip()}%"
            params.extend([term, term, term, term, term])

        sort_col = ALLOWED_SORT.get(filters.sort_by, "login")
        sort_dir = "DESC" if filters.sort_dir.lower() == "desc" else "ASC"
        where_sql = " AND ".join(where)

        count_sql = f"SELECT COUNT(*) AS total FROM prb_users WHERE {where_sql}"
        page = max(1, filters.page)
        page_size = max(1, min(100, filters.page_size))
        offset = (page - 1) * page_size

        list_sql = (
            f"SELECT * FROM prb_users WHERE {where_sql} "
            f"ORDER BY {sort_col} {sort_dir} NULLS LAST "
            f"LIMIT %s OFFSET %s"
        )

        with get_connection() as conn:
            total = int(conn.execute(count_sql, params).fetchone()["total"])
            rows = conn.execute(list_sql, [*params, page_size, offset]).fetchall()

        return [_row_to_user(r) for r in rows], total

    def insert(
        self,
        *,
        login: str,
        password_hash: str,
        profile: str,
        branch: Optional[str],
        display_name: Optional[str],
        name: Optional[str],
        code: Optional[str],
        report_emails: Optional[str],
        login_email: Optional[str] = None,
        enabled: bool,
        actor: str,
    ) -> User:
        sql = """
            INSERT INTO prb_users (
                login, password_hash, profile, branch, display_name, name, code,
                report_emails, login_email,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s,
                %s, NOW(), %s, NOW(), %s
            )
            RETURNING *
        """
        with get_connection() as conn:
            row = conn.execute(
                sql,
                [
                    login,
                    password_hash,
                    profile,
                    branch,
                    display_name,
                    name,
                    code,
                    report_emails,
                    login_email,
                    actor,
                    actor,
                    enabled,
                ],
            ).fetchone()
        return _row_to_user(row)

    def update(self, user_id: int, fields: dict[str, Any], actor: str) -> Optional[User]:
        if not fields:
            return self.get_by_id(user_id, include_disabled=True)

        allowed = {
            "login",
            "password_hash",
            "profile",
            "branch",
            "display_name",
            "name",
            "code",
            "report_emails",
            "login_email",
            "must_change_password",
            "temporary_password_expires_at",
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
        params.append(user_id)

        sql = f"UPDATE prb_users SET {', '.join(sets)} WHERE id = %s RETURNING *"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row_to_user(row) if row else None

    def soft_delete(self, user_id: int, actor: str) -> Optional[User]:
        return self.update(user_id, {"enabled": False}, actor)

    def list_active_filial_with_branch(self) -> list[User]:
        sql = """
            SELECT * FROM prb_users
            WHERE enabled = TRUE
              AND lower(profile) = 'filial'
              AND COALESCE(branch, '') <> ''
            ORDER BY branch, login
        """
        with get_connection() as conn:
            rows = conn.execute(sql).fetchall()
        return [_row_to_user(r) for r in rows]
