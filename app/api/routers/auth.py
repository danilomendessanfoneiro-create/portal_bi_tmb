"""Auth routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.api.schemas import LoginRequest, TokenResponse, UserOut
from app.models import User
from app.services import AuthService
from app.utils.jwt_tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_out(user: User) -> UserOut:
    return UserOut(
        id=int(user.id),
        login=user.login,
        profile=user.profile,
        branch=user.branch,
        display_name=user.display_name,
        name=user.name,
        code=user.code,
        enabled=user.enabled,
        created_on=user.created_on,
        modified_on=user.modified_on,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    user = AuthService().authenticate(body.login, body.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos")
    token = create_access_token(user)
    return TokenResponse(access_token=token, user=_to_out(user))


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return _to_out(user)
