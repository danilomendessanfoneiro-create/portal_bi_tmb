"""Job schedule admin routes."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import require_admin
from app.models import User
from app.services.job_schedule_service import JobScheduleError, JobScheduleService

router = APIRouter(prefix="/settings/schedules", tags=["settings-schedules"])


class ScheduleOut(BaseModel):
    id: int
    job_id: str
    display_name: Optional[str] = None
    local_time: str
    timezone: str
    frequency: str = "daily"
    weekday: Optional[int] = None
    day_of_month: Optional[int] = None
    enabled: bool


class ScheduleUpdateBody(BaseModel):
    local_time: Optional[str] = None
    timezone: Optional[str] = None
    frequency: Optional[str] = None
    weekday: Optional[int] = None
    day_of_month: Optional[int] = None
    enabled: Optional[bool] = None


def _to_out(item) -> ScheduleOut:
    return ScheduleOut(
        id=item.id,
        job_id=item.job_id,
        display_name=item.display_name,
        local_time=item.local_time,
        timezone=item.timezone,
        frequency=item.frequency or "daily",
        weekday=item.weekday,
        day_of_month=item.day_of_month,
        enabled=item.enabled,
    )


@router.get("", response_model=list[ScheduleOut])
def list_schedules(admin: Annotated[User, Depends(require_admin)]) -> list[ScheduleOut]:
    return [_to_out(i) for i in JobScheduleService().list()]


@router.get("/{job_id}", response_model=ScheduleOut)
def get_schedule(job_id: str, admin: Annotated[User, Depends(require_admin)]) -> ScheduleOut:
    item = JobScheduleService().get(job_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return _to_out(item)


@router.put("/{job_id}", response_model=ScheduleOut)
def update_schedule(
    job_id: str,
    body: ScheduleUpdateBody,
    admin: Annotated[User, Depends(require_admin)],
) -> ScheduleOut:
    try:
        item = JobScheduleService().update(
            job_id,
            local_time=body.local_time,
            timezone=body.timezone,
            frequency=body.frequency,
            weekday=body.weekday,
            day_of_month=body.day_of_month,
            enabled=body.enabled,
            actor=admin.login,
        )
    except JobScheduleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(item)
