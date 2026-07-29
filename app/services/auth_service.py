"""Auth business rules — no direct DB access outside repository."""

from __future__ import annotations

from typing import Optional

from app.models import User
from app.repositories import UserRepository
from app.utils.password import verify_password


class AuthService:
    def __init__(self, users: Optional[UserRepository] = None) -> None:
        self._users = users or UserRepository()

    def authenticate(self, login: str, password: str) -> Optional[User]:
        user = self._users.get_by_login(login.strip(), include_disabled=False)
        if user is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
