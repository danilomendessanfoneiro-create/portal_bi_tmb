"""Email recipients admin routes."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_admin
from app.api.schemas import (
    MessageOut,
    RecipientCreateBody,
    RecipientListResponse,
    RecipientOut,
    RecipientUpdateBody,
)
from app.models import User
from app.models.settings_models import EmailRecipient
from app.schemas import RecipientCreate, RecipientFilter, RecipientUpdate
from app.services import EmailRecipientService, RecipientServiceError

router = APIRouter(prefix="/settings/recipients", tags=["settings-recipients"])


def _to_out(item: EmailRecipient) -> RecipientOut:
    return RecipientOut(
        id=int(item.id),
        name=item.name,
        email=item.email,
        role_title=item.role_title,
        department=item.department,
        receive_daily=item.receive_daily,
        receive_weekly=item.receive_weekly,
        receive_monthly=item.receive_monthly,
        enabled=item.enabled,
        created_on=item.created_on,
        modified_on=item.modified_on,
    )


@router.get("", response_model=RecipientListResponse)
def list_recipients(
    admin: Annotated[User, Depends(require_admin)],
    search: Optional[str] = None,
    enabled: Optional[bool] = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort_by: str = "name",
    sort_dir: str = "asc",
    include_disabled: bool = False,
) -> RecipientListResponse:
    enabled_filter: Optional[bool] = None if include_disabled else enabled
    items, total = EmailRecipientService().list(
        RecipientFilter(
            search=search,
            enabled=enabled_filter,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )
    return RecipientListResponse(
        items=[_to_out(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=RecipientOut, status_code=status.HTTP_201_CREATED)
def create_recipient(
    body: RecipientCreateBody,
    admin: Annotated[User, Depends(require_admin)],
) -> RecipientOut:
    try:
        item = EmailRecipientService().create(
            RecipientCreate(
                name=body.name,
                email=body.email,
                role_title=body.role_title,
                department=body.department,
                receive_daily=body.receive_daily,
                receive_weekly=body.receive_weekly,
                receive_monthly=body.receive_monthly,
                enabled=body.enabled,
            ),
            actor=admin.login,
        )
    except RecipientServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(item)


@router.put("/{item_id}", response_model=RecipientOut)
def update_recipient(
    item_id: int,
    body: RecipientUpdateBody,
    admin: Annotated[User, Depends(require_admin)],
) -> RecipientOut:
    try:
        item = EmailRecipientService().update(
            item_id,
            RecipientUpdate(
                name=body.name,
                email=body.email,
                role_title=body.role_title,
                department=body.department,
                receive_daily=body.receive_daily,
                receive_weekly=body.receive_weekly,
                receive_monthly=body.receive_monthly,
                enabled=body.enabled,
            ),
            actor=admin.login,
        )
    except RecipientServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(item)


@router.delete("/{item_id}", response_model=MessageOut)
def deactivate_recipient(
    item_id: int,
    admin: Annotated[User, Depends(require_admin)],
) -> MessageOut:
    try:
        EmailRecipientService().soft_delete(item_id, actor=admin.login)
    except RecipientServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageOut(detail="Destinatário desativado")
