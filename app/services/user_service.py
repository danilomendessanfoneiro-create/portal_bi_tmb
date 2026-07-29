"""User management business rules."""

from __future__ import annotations

from typing import Optional

from app.models import User
from app.repositories import UserRepository
from app.schemas import UserCreate, UserFilter, UserUpdate
from app.utils.password import hash_password
from app.utils.report_emails import normalize_report_emails, validate_report_emails


class UserServiceError(Exception):
    pass


class UserService:
    def __init__(self, users: Optional[UserRepository] = None) -> None:
        self._users = users or UserRepository()

    def get(self, user_id: int) -> Optional[User]:
        return self._users.get_by_id(user_id, include_disabled=True)

    def list(self, filters: UserFilter) -> tuple[list[User], int]:
        return self._users.list(filters)

    def create(self, data: UserCreate, actor: str) -> User:
        login = data.login.strip()
        if not login:
            raise UserServiceError("Login é obrigatório.")
        if not data.password:
            raise UserServiceError("Senha é obrigatória.")
        profile = (data.profile or "").strip().lower()
        if profile not in {"admin", "filial"}:
            raise UserServiceError("Perfil deve ser 'admin' ou 'filial'.")
        if profile == "filial" and not (data.branch or "").strip():
            raise UserServiceError("Filial é obrigatória para perfil filial.")
        if self._users.get_by_login(login, include_disabled=True):
            raise UserServiceError("Já existe um usuário com este login.")

        report_emails = self._resolve_report_emails(profile, data.report_emails)

        return self._users.insert(
            login=login,
            password_hash=hash_password(data.password),
            profile=profile,
            branch=(data.branch or "").strip() or None,
            display_name=(data.display_name or data.name or login).strip(),
            name=(data.name or data.display_name or login).strip(),
            code=(data.code or login).strip(),
            report_emails=report_emails,
            enabled=bool(data.enabled),
            actor=actor,
        )

    def update(self, user_id: int, data: UserUpdate, actor: str) -> User:
        current = self._users.get_by_id(user_id, include_disabled=True)
        if current is None:
            raise UserServiceError("Usuário não encontrado.")

        fields: dict = {}
        if data.login is not None:
            login = data.login.strip()
            if not login:
                raise UserServiceError("Login é obrigatório.")
            other = self._users.get_by_login(login, include_disabled=True)
            if other and other.id != user_id:
                raise UserServiceError("Já existe um usuário com este login.")
            fields["login"] = login

        if data.password:
            fields["password_hash"] = hash_password(data.password)

        if data.profile is not None:
            profile = data.profile.strip().lower()
            if profile not in {"admin", "filial"}:
                raise UserServiceError("Perfil deve ser 'admin' ou 'filial'.")
            fields["profile"] = profile

        if data.branch is not None:
            fields["branch"] = data.branch.strip() or None
        if data.display_name is not None:
            fields["display_name"] = data.display_name.strip() or None
        if data.name is not None:
            fields["name"] = data.name.strip() or None
        if data.code is not None:
            fields["code"] = data.code.strip() or None
        if data.enabled is not None:
            fields["enabled"] = bool(data.enabled)

        profile = fields.get("profile", current.profile)
        branch = fields.get("branch", current.branch) if "branch" in fields else current.branch
        if profile == "filial" and not (branch or "").strip():
            raise UserServiceError("Filial é obrigatória para perfil filial.")

        if data.report_emails is not None or "profile" in fields:
            raw = data.report_emails if data.report_emails is not None else current.report_emails
            fields["report_emails"] = self._resolve_report_emails(profile, raw)

        updated = self._users.update(user_id, fields, actor)
        if updated is None:
            raise UserServiceError("Falha ao atualizar usuário.")
        return updated

    def soft_delete(self, user_id: int, actor: str) -> User:
        current = self._users.get_by_id(user_id, include_disabled=True)
        if current is None:
            raise UserServiceError("Usuário não encontrado.")
        if current.login == actor:
            raise UserServiceError("Não é permitido desativar o próprio usuário.")
        updated = self._users.soft_delete(user_id, actor)
        if updated is None:
            raise UserServiceError("Falha ao desativar usuário.")
        return updated

    def list_filial_for_reports(self) -> list[User]:
        return self._users.list_active_filial_with_branch()

    @staticmethod
    def _resolve_report_emails(profile: str, raw: Optional[str]) -> Optional[str]:
        if (profile or "").lower() != "filial":
            return None
        try:
            emails = validate_report_emails(raw)
        except ValueError as exc:
            raise UserServiceError(str(exc)) from exc
        return normalize_report_emails(";".join(emails)) if emails else None
