"""Clients admin routes."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_admin
from app.api.schemas import (
    ClientCreateBody,
    ClientListResponse,
    ClientOut,
    ClientUpdateBody,
    MessageOut,
)
from app.models import User
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientFilter, ClientUpdate
from app.services import ClientService, ClientServiceError

router = APIRouter(prefix="/settings/clients", tags=["settings-clients"])


def _to_out(item: Client) -> ClientOut:
    return ClientOut(
        id=int(item.id),
        name=item.name,
        cnpj=item.cnpj,
        emails=item.emails,
        enabled=item.enabled,
        created_on=item.created_on,
        modified_on=item.modified_on,
    )


@router.get("", response_model=ClientListResponse)
def list_clients(
    admin: Annotated[User, Depends(require_admin)],
    search: Optional[str] = None,
    enabled: Optional[bool] = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort_by: str = "name",
    sort_dir: str = "asc",
    include_disabled: bool = False,
) -> ClientListResponse:
    enabled_filter: Optional[bool] = None if include_disabled else enabled
    items, total = ClientService().list(
        ClientFilter(
            search=search,
            enabled=enabled_filter,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )
    return ClientListResponse(
        items=[_to_out(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    body: ClientCreateBody,
    admin: Annotated[User, Depends(require_admin)],
) -> ClientOut:
    try:
        item = ClientService().create(
            ClientCreate(
                name=body.name,
                cnpj=body.cnpj,
                emails=body.emails,
                enabled=body.enabled,
            ),
            actor=admin.login,
        )
    except ClientServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(item)


@router.put("/{item_id}", response_model=ClientOut)
def update_client(
    item_id: int,
    body: ClientUpdateBody,
    admin: Annotated[User, Depends(require_admin)],
) -> ClientOut:
    try:
        item = ClientService().update(
            item_id,
            ClientUpdate(
                name=body.name,
                cnpj=body.cnpj,
                emails=body.emails,
                enabled=body.enabled,
            ),
            actor=admin.login,
        )
    except ClientServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(item)


@router.delete("/{item_id}", response_model=MessageOut)
def deactivate_client(
    item_id: int,
    admin: Annotated[User, Depends(require_admin)],
) -> MessageOut:
    try:
        ClientService().soft_delete(item_id, actor=admin.login)
    except ClientServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageOut(detail="Cliente desativado")
