"""Auth routes."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.api.schemas import (
    ChangeOwnPasswordBody,
    ForgotPasswordBody,
    LoginRequest,
    MessageOut,
    ResetPasswordBody,
    ResetTokenStatusOut,
    TokenResponse,
    UserOut,
)
from app.models import User
from app.services import AuthService, UserService, UserServiceError
from app.services.auth_service import AuthError
from app.services.password_recovery_service import PasswordRecoveryService
from app.utils.hcaptcha import HCaptchaError, verify_hcaptcha
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
        report_emails=user.report_emails,
        login_email=user.login_email,
        must_change_password=bool(user.must_change_password),
        enabled=user.enabled,
        created_on=user.created_on,
        modified_on=user.modified_on,
    )


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request) -> TokenResponse:
    try:
        verify_hcaptcha(body.hcaptcha_token, remote_ip=_client_ip(request))
    except HCaptchaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        user = AuthService().authenticate(body.login, body.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message
        ) from exc
    token = create_access_token(user)
    return TokenResponse(access_token=token, user=_to_out(user))


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return _to_out(user)


@router.post("/change-password", response_model=MessageOut)
def change_password(
    body: ChangeOwnPasswordBody,
    user: Annotated[User, Depends(get_current_user)],
) -> MessageOut:
    try:
        UserService().change_own_password(
            user,
            current_password=body.current_password,
            new_password=body.new_password,
            confirm_password=body.confirm_password,
        )
    except UserServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MessageOut(detail="Senha alterada com sucesso")


@router.post("/forgot-password", response_model=MessageOut)
def forgot_password(body: ForgotPasswordBody) -> MessageOut:
    result = PasswordRecoveryService().request_reset(body.email)
    return MessageOut(detail=result.message)


@router.get("/reset-password", response_model=ResetTokenStatusOut)
def reset_password_status(token: str = "") -> ResetTokenStatusOut:
    validation = PasswordRecoveryService().validate_token(token)
    return ResetTokenStatusOut(valid=validation.valid, detail=validation.message)


@router.post("/reset-password", response_model=MessageOut)
def reset_password(body: ResetPasswordBody) -> MessageOut:
    try:
        PasswordRecoveryService().reset_password(
            raw_token=body.token,
            new_password=body.new_password,
            confirm_password=body.confirm_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MessageOut(detail="Senha redefinida com sucesso. Faça login com a nova senha.")
