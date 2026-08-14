"""Job schedule business rules."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from app.repositories.job_schedule_repository import JobSchedule, JobScheduleRepository
from app.utils.secret_box import decrypt_secret, encrypt_secret

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
FREQUENCIES = {"daily", "weekly", "monthly"}
# Após o horário agendado, o timer (--if-due) só tenta nesta janela; depois, só manual/--force.
DUE_GRACE_MINUTES = 60

AUTOMATION_BRANCH = "report_branch_daily"
AUTOMATION_MANAGERIAL = "report_managerial"
AUTOMATION_CLIENT = "report_client_daily"
AUTOMATION_TMS_SPREADSHEET = "fetch_tmselite_spreadsheet"
DEFAULT_TMS_LOGIN_URL = "https://tmblogistica.tmselite.com/login"
DEFAULT_RUN_WEEKDAYS = [1, 2, 3, 4, 5, 6]
VISIBLE_AUTOMATIONS = (
    AUTOMATION_TMS_SPREADSHEET,
    AUTOMATION_BRANCH,
    AUTOMATION_CLIENT,
    AUTOMATION_MANAGERIAL,
)
API_AUTOMATIONS = (
    "import_deliveries_daily",
    "import_deliveries_initial",
)
# Alias legado — não listar na UI
HIDDEN_API_AUTOMATIONS = (
    "import_deliveries",
)


class JobScheduleError(Exception):
    pass


def prd_weekday(dt: datetime) -> int:
    """Python Monday=0 … Sunday=6 → 0=Domingo … 6=Sábado."""
    return (dt.weekday() + 1) % 7


def normalize_run_weekdays(days: list[int]) -> list[int]:
    uniq = sorted({int(d) for d in days})
    if not uniq:
        raise JobScheduleError("Selecione pelo menos um dia da semana.")
    if any(d < 0 or d > 6 for d in uniq):
        raise JobScheduleError("Dias da semana devem ser 0 (Domingo) a 6 (Sábado).")
    return uniq


class JobScheduleService:
    def __init__(self, repo: Optional[JobScheduleRepository] = None) -> None:
        self._repo = repo or JobScheduleRepository()

    def get(self, job_id: str) -> Optional[JobSchedule]:
        return self._repo.get_by_job_id(job_id)

    def list(self) -> list[JobSchedule]:
        hidden = set(HIDDEN_API_AUTOMATIONS)
        items = [item for item in self._repo.list_all() if item.job_id not in hidden]
        order = {
            AUTOMATION_TMS_SPREADSHEET: 0,
            "import_deliveries_daily": 1,
            "import_deliveries_initial": 2,
            AUTOMATION_BRANCH: 3,
            AUTOMATION_CLIENT: 4,
            AUTOMATION_MANAGERIAL: 5,
        }
        return sorted(items, key=lambda s: (order.get(s.job_id, 50), s.job_id))

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
        tms_login_url: Optional[str] = None,
        tms_username: Optional[str] = None,
        tms_password: Optional[str] = None,
        run_weekdays: Optional[list[int]] = None,
        actor: str,
    ) -> JobSchedule:
        current = self.get(job_id)
        if current is None:
            raise JobScheduleError("Agendamento não encontrado.")

        if job_id in API_AUTOMATIONS:
            if enabled is True:
                raise JobScheduleError(
                    "Job da API permanece desabilitado. Use Importação de pedidos."
                )
            enabled = False

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
        if job_id == AUTOMATION_CLIENT and freq != "daily":
            raise JobScheduleError("Automação dos clientes permite apenas frequência diária.")
        if job_id == AUTOMATION_TMS_SPREADSHEET and freq != "daily":
            raise JobScheduleError("Importação de pedidos permite apenas frequência diária.")

        url = current.tms_login_url
        user = current.tms_username
        password_encrypted = None
        if job_id == AUTOMATION_TMS_SPREADSHEET:
            if tms_login_url is not None:
                url = tms_login_url.strip() or DEFAULT_TMS_LOGIN_URL
            if tms_username is not None:
                user = tms_username.strip() or None
            if tms_password:
                password_encrypted = encrypt_secret(tms_password)
            will_enable = current.enabled if enabled is None else bool(enabled)
            if will_enable:
                if not url:
                    raise JobScheduleError("URL de login do TMS é obrigatória.")
                if not user:
                    raise JobScheduleError("Usuário do TMS é obrigatório.")
                has_secret = bool(password_encrypted or current.tms_password_encrypted)
                if not has_secret:
                    raise JobScheduleError("Senha do TMS é obrigatória para ativar a importação.")
        elif tms_login_url is not None or tms_username is not None or tms_password:
            raise JobScheduleError("Credenciais TMS só se aplicam à Importação de pedidos.")


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

        days = None
        if run_weekdays is not None:
            days = normalize_run_weekdays(run_weekdays)

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
            tms_login_url=url if job_id == AUTOMATION_TMS_SPREADSHEET and tms_login_url is not None else None,
            tms_username=user if job_id == AUTOMATION_TMS_SPREADSHEET and tms_username is not None else None,
            tms_password_encrypted=password_encrypted,
            run_weekdays=days,
            actor=actor,
        )
        if updated is None:
            raise JobScheduleError("Agendamento não encontrado.")
        return updated

    def get_tms_password(self, job_id: str = AUTOMATION_TMS_SPREADSHEET) -> Optional[str]:
        sched = self.get(job_id)
        if sched is None or not sched.tms_password_encrypted:
            return None
        return decrypt_secret(sched.tms_password_encrypted)

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
        scheduled_at = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
        window_end = scheduled_at + timedelta(minutes=DUE_GRACE_MINUTES)
        if current < scheduled_at or current > window_end:
            return False

        days = sched.run_weekdays if sched.run_weekdays is not None else DEFAULT_RUN_WEEKDAYS
        if not days or prd_weekday(current) not in {int(d) for d in days}:
            return False

        freq = (sched.frequency or "daily").lower()
        if freq == "daily":
            return True
        if freq == "weekly":
            return sched.weekday is not None and int(sched.weekday) == prd_weekday(current)
        if freq == "monthly":
            return sched.day_of_month is not None and int(sched.day_of_month) == current.day
        return False
