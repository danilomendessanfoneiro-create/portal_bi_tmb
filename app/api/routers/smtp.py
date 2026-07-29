"""SMTP settings admin routes."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_admin
from app.api.schemas import MessageOut, SmtpCreateBody, SmtpListResponse, SmtpOut, SmtpUpdateBody
from app.models import User
from app.models.settings_models import SmtpSettings
from app.schemas import SmtpCreate, SmtpFilter, SmtpUpdate
from app.services import SmtpServiceError, SmtpSettingsService

router = APIRouter(prefix="/settings/smtp", tags=["settings-smtp"])


def _to_out(item: SmtpSettings) -> SmtpOut:
    return SmtpOut(
        id=int(item.id),
        name=item.name,
        host=item.host,
        port=item.port,
        username=item.username,
        use_tls=item.use_tls,
        sender_email=item.sender_email,
        sender_name=item.sender_name,
        timeout_seconds=item.timeout_seconds,
        is_default=item.is_default,
        enabled=item.enabled,
        created_on=item.created_on,
        modified_on=item.modified_on,
    )


@router.get("", response_model=SmtpListResponse)
def list_smtp(
    admin: Annotated[User, Depends(require_admin)],
    search: Optional[str] = None,
    enabled: Optional[bool] = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort_by: str = "name",
    sort_dir: str = "asc",
    include_disabled: bool = False,
) -> SmtpListResponse:
    enabled_filter: Optional[bool] = None if include_disabled else enabled
    items, total = SmtpSettingsService().list(
        SmtpFilter(
            search=search,
            enabled=enabled_filter,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )
    return SmtpListResponse(
        items=[_to_out(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=SmtpOut, status_code=status.HTTP_201_CREATED)
def create_smtp(body: SmtpCreateBody, admin: Annotated[User, Depends(require_admin)]) -> SmtpOut:
    try:
        item = SmtpSettingsService().create(
            SmtpCreate(
                name=body.name,
                host=body.host,
                port=body.port,
                username=body.username,
                password=body.password,
                use_tls=body.use_tls,
                sender_email=body.sender_email,
                sender_name=body.sender_name,
                timeout_seconds=body.timeout_seconds,
                is_default=body.is_default,
                enabled=body.enabled,
            ),
            actor=admin.login,
        )
    except SmtpServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(item)


@router.put("/{item_id}", response_model=SmtpOut)
def update_smtp(
    item_id: int,
    body: SmtpUpdateBody,
    admin: Annotated[User, Depends(require_admin)],
) -> SmtpOut:
    try:
        item = SmtpSettingsService().update(
            item_id,
            SmtpUpdate(
                name=body.name,
                host=body.host,
                port=body.port,
                username=body.username,
                password=body.password,
                use_tls=body.use_tls,
                sender_email=body.sender_email,
                sender_name=body.sender_name,
                timeout_seconds=body.timeout_seconds,
                is_default=body.is_default,
                enabled=body.enabled,
            ),
            actor=admin.login,
        )
    except SmtpServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(item)


@router.delete("/{item_id}", response_model=MessageOut)
def deactivate_smtp(item_id: int, admin: Annotated[User, Depends(require_admin)]) -> MessageOut:
    try:
        SmtpSettingsService().soft_delete(item_id, actor=admin.login)
    except SmtpServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageOut(detail="Configuração SMTP desativada")
