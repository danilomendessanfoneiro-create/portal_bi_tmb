"""Auth business rules — no direct DB access outside repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.models import User
from app.repositories import UserRepository
from app.utils.password import verify_password


class AuthError(Exception):
    """Authentication rejected with a user-facing message."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthService:
    def __init__(self, users: Optional[UserRepository] = None) -> None:
        self._users = users or UserRepository()

    def authenticate(self, login: str, password: str) -> User:
        user = self._users.get_by_login(login.strip(), include_disabled=False)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthError("Usuário ou senha inválidos")
        if user.must_change_password and user.temporary_password_expires_at is not None:
            expires = user.temporary_password_expires_at
            if getattr(expires, "tzinfo", None) is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires:
                raise AuthError(
                    "A senha provisória expirou. Solicite uma nova ao administrador "
                    "ou use a recuperação de senha."
                )
        return user
