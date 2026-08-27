"""Users admin routes."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_admin
from app.api.schemas import (
    AdminSetPasswordBody,
    AdminSetPasswordOut,
    MessageOut,
    UserCreateBody,
    UserListResponse,
    UserOut,
    UserUpdateBody,
)
from app.models import User
from app.schemas import UserCreate, UserFilter, UserUpdate
from app.services import UserService, UserServiceError

router = APIRouter(prefix="/users", tags=["users"])


def _to_out(user: User) -> UserOut:
    return UserOut(
        id=int(user.id),
        login=user.login,
        profile=user.profile,
        branch=user.branch,
        display_name=user.display_name,
        name=user.name,
        code=user.code,
        report_emails=user.report_emails,
        login_email=user.login_email,
        must_change_password=bool(user.must_change_password),
        enabled=user.enabled,
        created_on=user.created_on,
        modified_on=user.modified_on,
    )


@router.get("", response_model=UserListResponse)
def list_users(
    admin: Annotated[User, Depends(require_admin)],
    search: Optional[str] = None,
    profile: Optional[str] = None,
    enabled: Optional[bool] = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort_by: str = "login",
    sort_dir: str = "asc",
    include_disabled: bool = False,
) -> UserListResponse:
    enabled_filter: Optional[bool]
    if include_disabled:
        enabled_filter = None
    else:
        enabled_filter = enabled
    items, total = UserService().list(
        UserFilter(
            search=search,
            profile=profile,
            enabled=enabled_filter,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )
    return UserListResponse(
        items=[_to_out(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, admin: Annotated[User, Depends(require_admin)]) -> UserOut:
    user = UserService().get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return _to_out(user)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreateBody, admin: Annotated[User, Depends(require_admin)]) -> UserOut:
    try:
        user = UserService().create(
            UserCreate(
                login=body.login,
                password=body.password or "",
                profile=body.profile,
                branch=body.branch,
                display_name=body.display_name,
                name=body.name,
                code=body.code,
                report_emails=body.report_emails,
                login_email=body.login_email,
                enabled=body.enabled,
                send_provisional=bool(body.send_provisional),
            ),
            actor=admin.login,
        )
    except UserServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(user)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdateBody,
    admin: Annotated[User, Depends(require_admin)],
) -> UserOut:
    try:
        user = UserService().update(
            user_id,
            UserUpdate(
                login=body.login,
                password=body.password,
                profile=body.profile,
                branch=body.branch,
                display_name=body.display_name,
                name=body.name,
                code=body.code,
                report_emails=body.report_emails,
                login_email=body.login_email,
                enabled=body.enabled,
            ),
            actor=admin.login,
        )
    except UserServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(user)


@router.post("/{user_id}/password", response_model=AdminSetPasswordOut)
def set_user_password(
    user_id: int,
    body: AdminSetPasswordBody,
    admin: Annotated[User, Depends(require_admin)],
) -> AdminSetPasswordOut:
    try:
        _user, generated = UserService().set_password_admin(
            user_id,
            password=body.password,
            generate=bool(body.generate),
            actor=admin.login,
        )
    except UserServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AdminSetPasswordOut(
        detail="Senha atualizada",
        generated_password=generated,
    )


@router.post("/{user_id}/provisional-password", response_model=MessageOut)
def send_provisional_password(
    user_id: int,
    admin: Annotated[User, Depends(require_admin)],
) -> MessageOut:
    try:
        UserService().send_provisional_password(user_id, actor=admin.login)
    except UserServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageOut(detail="Senha provisória enviada por e-mail")


@router.delete("/{user_id}", response_model=MessageOut)
def deactivate_user(user_id: int, admin: Annotated[User, Depends(require_admin)]) -> MessageOut:
    try:
        UserService().soft_delete(user_id, actor=admin.login)
    except UserServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageOut(detail="Usuário desativado")
