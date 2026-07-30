"""API integration settings admin routes."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_admin
from app.api.schemas import (
    ApiSettingsCreateBody,
    ApiSettingsListResponse,
    ApiSettingsOut,
    ApiSettingsUpdateBody,
    MessageOut,
)
from app.models import User
from app.models.settings_models import ApiSettings
from app.schemas import ApiSettingsCreate, ApiSettingsFilter, ApiSettingsUpdate
from app.services.api_settings_service import ApiSettingsService, ApiSettingsServiceError

router = APIRouter(prefix="/settings/api-integration", tags=["settings-api-integration"])


def _to_out(item: ApiSettings) -> ApiSettingsOut:
    return ApiSettingsOut(
        id=int(item.id),
        name=item.name,
        base_url=item.base_url,
        endpoint=item.endpoint,
        timeout_seconds=item.timeout_seconds,
        page_size=item.page_size,
        initial_load_days=item.initial_load_days,
        is_default=item.is_default,
        enabled=item.enabled,
        has_token=bool(item.token_encrypted),
        created_on=item.created_on,
        modified_on=item.modified_on,
    )


@router.get("", response_model=ApiSettingsListResponse)
def list_api_settings(
    admin: Annotated[User, Depends(require_admin)],
    search: Optional[str] = None,
    enabled: Optional[bool] = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort_by: str = "name",
    sort_dir: str = "asc",
    include_disabled: bool = False,
) -> ApiSettingsListResponse:
    enabled_filter: Optional[bool] = None if include_disabled else enabled
    items, total = ApiSettingsService().list(
        ApiSettingsFilter(
            search=search,
            enabled=enabled_filter,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )
    return ApiSettingsListResponse(
        items=[_to_out(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ApiSettingsOut, status_code=status.HTTP_201_CREATED)
def create_api_settings(
    body: ApiSettingsCreateBody,
    admin: Annotated[User, Depends(require_admin)],
) -> ApiSettingsOut:
    try:
        item = ApiSettingsService().create(
            ApiSettingsCreate(
                name=body.name,
                base_url=body.base_url,
                endpoint=body.endpoint,
                token=body.token,
                timeout_seconds=body.timeout_seconds,
                page_size=body.page_size,
                initial_load_days=body.initial_load_days,
                is_default=body.is_default,
                enabled=body.enabled,
            ),
            actor=admin.login,
        )
    except ApiSettingsServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(item)


@router.put("/{item_id}", response_model=ApiSettingsOut)
def update_api_settings(
    item_id: int,
    body: ApiSettingsUpdateBody,
    admin: Annotated[User, Depends(require_admin)],
) -> ApiSettingsOut:
    try:
        item = ApiSettingsService().update(
            item_id,
            ApiSettingsUpdate(
                name=body.name,
                base_url=body.base_url,
                endpoint=body.endpoint,
                token=body.token,
                timeout_seconds=body.timeout_seconds,
                page_size=body.page_size,
                initial_load_days=body.initial_load_days,
                is_default=body.is_default,
                enabled=body.enabled,
            ),
            actor=admin.login,
        )
    except ApiSettingsServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(item)


@router.delete("/{item_id}", response_model=MessageOut)
def deactivate_api_settings(
    item_id: int,
    admin: Annotated[User, Depends(require_admin)],
) -> MessageOut:
    try:
        ApiSettingsService().soft_delete(item_id, actor=admin.login)
    except ApiSettingsServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageOut(detail="Configuração desativada")
