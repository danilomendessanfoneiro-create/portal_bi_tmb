"""Job schedule settings repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.repositories.base import get_connection


@dataclass
class JobSchedule:
    id: int
    job_id: str
    local_time: str
    timezone: str
    enabled: bool
    display_name: Optional[str] = None
    frequency: str = "daily"
    weekday: Optional[int] = None
    day_of_month: Optional[int] = None
    tms_login_url: Optional[str] = None
    tms_username: Optional[str] = None
    tms_password_encrypted: Optional[str] = None
    run_weekdays: Optional[list[int]] = None
    created_by: Optional[str] = None
    created_on: Optional[datetime] = None
    modified_by: Optional[str] = None
    modified_on: Optional[datetime] = None


def _weekdays(value: Any) -> list[int]:
    if value is None:
        return [1, 2, 3, 4, 5, 6]
    return [int(v) for v in list(value)]


def _row(row: dict[str, Any]) -> JobSchedule:
    return JobSchedule(
        id=int(row["id"]),
        job_id=row["job_id"],
        local_time=row["local_time"],
        timezone=row["timezone"] or "America/Sao_Paulo",
        enabled=bool(row["enabled"]),
        display_name=row.get("display_name"),
        frequency=(row.get("frequency") or "daily").lower(),
        weekday=row.get("weekday"),
        day_of_month=row.get("day_of_month"),
        tms_login_url=row.get("tms_login_url"),
        tms_username=row.get("tms_username"),
        tms_password_encrypted=row.get("tms_password_encrypted"),
        run_weekdays=_weekdays(row.get("run_weekdays")),
        created_by=row.get("created_by"),
        created_on=row.get("created_on"),
        modified_by=row.get("modified_by"),
        modified_on=row.get("modified_on"),
    )


class JobScheduleRepository:
    def get_by_job_id(self, job_id: str) -> Optional[JobSchedule]:
        sql = "SELECT * FROM prb_job_settings WHERE job_id = %s"
        with get_connection() as conn:
            row = conn.execute(sql, [job_id]).fetchone()
        return _row(row) if row else None

    def list_all(self) -> list[JobSchedule]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM prb_job_settings ORDER BY display_name NULLS LAST, job_id"
            ).fetchall()
        return [_row(r) for r in rows]

    def update(
        self,
        job_id: str,
        *,
        local_time: Optional[str] = None,
        timezone: Optional[str] = None,
        enabled: Optional[bool] = None,
        display_name: Optional[str] = None,
        frequency: Optional[str] = None,
        weekday: Optional[int] = None,
        day_of_month: Optional[int] = None,
        clear_weekday: bool = False,
        clear_day_of_month: bool = False,
        tms_login_url: Optional[str] = None,
        tms_username: Optional[str] = None,
        tms_password_encrypted: Optional[str] = None,
        run_weekdays: Optional[list[int]] = None,
        actor: str,
    ) -> Optional[JobSchedule]:
        current = self.get_by_job_id(job_id)
        if current is None:
            return None
        fields = []
        params: list[Any] = []
        if local_time is not None:
            fields.append("local_time = %s")
            params.append(local_time)
        if timezone is not None:
            fields.append("timezone = %s")
            params.append(timezone)
        if enabled is not None:
            fields.append("enabled = %s")
            params.append(enabled)
        if display_name is not None:
            fields.append("display_name = %s")
            params.append(display_name)
        if frequency is not None:
            fields.append("frequency = %s")
            params.append(frequency)
        if clear_weekday:
            fields.append("weekday = NULL")
        elif weekday is not None:
            fields.append("weekday = %s")
            params.append(weekday)
        if clear_day_of_month:
            fields.append("day_of_month = NULL")
        elif day_of_month is not None:
            fields.append("day_of_month = %s")
            params.append(day_of_month)
        if tms_login_url is not None:
            fields.append("tms_login_url = %s")
            params.append(tms_login_url)
        if tms_username is not None:
            fields.append("tms_username = %s")
            params.append(tms_username)
        if tms_password_encrypted is not None:
            fields.append("tms_password_encrypted = %s")
            params.append(tms_password_encrypted)
        if run_weekdays is not None:
            fields.append("run_weekdays = %s")
            params.append(run_weekdays)
        if not fields:
            return current
        fields.append("modified_by = %s")
        params.append(actor)
        fields.append("modified_on = NOW()")
        params.append(job_id)
        sql = f"UPDATE prb_job_settings SET {', '.join(fields)} WHERE job_id = %s RETURNING *"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _row(row) if row else None
