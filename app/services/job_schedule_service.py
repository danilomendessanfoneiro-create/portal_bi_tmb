"""Job schedule business rules."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from app.repositories.job_schedule_repository import JobSchedule, JobScheduleRepository

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
FREQUENCIES = {"daily", "weekly", "monthly"}

AUTOMATION_BRANCH = "report_branch_daily"
AUTOMATION_MANAGERIAL = "report_managerial"


class JobScheduleError(Exception):
    pass


class JobScheduleService:
    def __init__(self, repo: Optional[JobScheduleRepository] = None) -> None:
        self._repo = repo or JobScheduleRepository()

    def get(self, job_id: str) -> Optional[JobSchedule]:
        return self._repo.get_by_job_id(job_id)

    def list(self) -> list[JobSchedule]:
        return self._repo.list_all()

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
        actor: str,
    ) -> JobSchedule:
        current = self.get(job_id)
        if current is None:
            raise JobScheduleError("Agendamento não encontrado.")

        if local_time is not None and not TIME_RE.match(local_time.strip()):
            raise JobScheduleError("Horário inválido. Use HH:MM (24h).")
        if timezone is not None:
            try:
                ZoneInfo(timezone)
            except Exception as exc:
                raise JobScheduleError("Timezone inválida.") from exc

        freq = (frequency or current.frequency or "daily").strip().lower()
        if freq not in FREQUENCIES:
            raise JobScheduleError("Frequência deve ser daily, weekly ou monthly.")

        if job_id == AUTOMATION_BRANCH and freq != "daily":
            raise JobScheduleError("Automação das filiais permite apenas frequência diária.")

        clear_weekday = False
        clear_day = False
        wd = weekday if weekday is not None else current.weekday
        dom = day_of_month if day_of_month is not None else current.day_of_month

        if freq == "daily":
            clear_weekday = True
            clear_day = True
            wd = None
            dom = None
        elif freq == "weekly":
            clear_day = True
            dom = None
            if wd is None or not (0 <= int(wd) <= 6):
                raise JobScheduleError("Dia da semana é obrigatório (0=Domingo … 6=Sábado).")
            wd = int(wd)
        elif freq == "monthly":
            clear_weekday = True
            wd = None
            if dom is None or not (1 <= int(dom) <= 31):
                raise JobScheduleError("Dia do mês deve ser entre 1 e 31.")
            dom = int(dom)

        updated = self._repo.update(
            job_id,
            local_time=local_time.strip() if local_time else None,
            timezone=timezone.strip() if timezone else None,
            enabled=enabled,
            display_name=display_name.strip() if display_name else None,
            frequency=freq,
            weekday=wd,
            day_of_month=dom,
            clear_weekday=clear_weekday,
            clear_day_of_month=clear_day,
            actor=actor,
        )
        if updated is None:
            raise JobScheduleError("Agendamento não encontrado.")
        return updated

    def is_due(self, job_id: str, *, now: Optional[datetime] = None) -> bool:
        sched = self.get(job_id)
        if sched is None or not sched.enabled:
            return False
        tz = ZoneInfo(sched.timezone)
        current = now.astimezone(tz) if now and now.tzinfo else (now or datetime.now(tz))
        if current.tzinfo is None:
            current = current.replace(tzinfo=tz)
        else:
            current = current.astimezone(tz)

        hour, minute = map(int, sched.local_time.split(":"))
        scheduled_minutes = hour * 60 + minute
        now_minutes = current.hour * 60 + current.minute
        if now_minutes < scheduled_minutes:
            return False

        freq = (sched.frequency or "daily").lower()
        if freq == "daily":
            return True
        if freq == "weekly":
            # Python: Monday=0 … Sunday=6 → PRD: Sunday=0 … Saturday=6
            py_wd = current.weekday()
            prd_wd = (py_wd + 1) % 7
            return sched.weekday is not None and int(sched.weekday) == prd_wd
        if freq == "monthly":
            return sched.day_of_month is not None and int(sched.day_of_month) == current.day
        return False
