"""User management business rules."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models import User
from app.repositories import UserRepository
from app.schemas import UserCreate, UserFilter, UserUpdate
from app.utils.access_audit import audit_access_event
from app.utils.access_email import PROVISIONAL_PASSWORD_HOURS, build_provisional_access_email
from app.utils.login_email import validate_login_email
from app.utils.outbound_mail import OutboundMailError, resolve_default_smtp, send_plain_email
from app.utils.password import (
    generate_secure_password,
    hash_password,
    validate_password_policy,
    verify_password,
)
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
        profile = (data.profile or "").strip().lower()
        if profile not in {"admin", "filial"}:
            raise UserServiceError("Perfil deve ser 'admin' ou 'filial'.")
        if profile == "filial" and not (data.branch or "").strip():
            raise UserServiceError("Filial é obrigatória para perfil filial.")
        if self._users.get_by_login(login, include_disabled=True):
            raise UserServiceError("Já existe um usuário com este login.")

        try:
            login_email = validate_login_email(data.login_email)
        except ValueError as exc:
            raise UserServiceError(str(exc)) from exc
        if login_email and self._users.get_by_login_email(login_email, include_disabled=True):
            raise UserServiceError("Já existe um usuário com este e-mail de login.")

        send_provisional = bool(data.send_provisional)
        if send_provisional and not login_email:
            raise UserServiceError(
                "Cadastre o e-mail de login para enviar senha provisória."
            )

        plain_password = data.password
        must_change = False
        temp_expires = None
        if send_provisional:
            plain_password = generate_secure_password()
            must_change = True
            temp_expires = datetime.now(timezone.utc) + timedelta(
                hours=PROVISIONAL_PASSWORD_HOURS
            )
        elif not plain_password:
            raise UserServiceError("Senha é obrigatória.")
        try:
            validate_password_policy(plain_password)
        except ValueError as exc:
            raise UserServiceError(str(exc)) from exc

        report_emails = self._resolve_report_emails(profile, data.report_emails)

        created = self._users.insert(
            login=login,
            password_hash=hash_password(plain_password),
            profile=profile,
            branch=(data.branch or "").strip() or None,
            display_name=(data.display_name or data.name or login).strip(),
            name=(data.name or data.display_name or login).strip(),
            code=(data.code or login).strip(),
            report_emails=report_emails,
            login_email=login_email,
            enabled=bool(data.enabled),
            actor=actor,
        )
        if must_change and created.id is not None:
            created = self._users.update(
                int(created.id),
                {
                    "must_change_password": True,
                    "temporary_password_expires_at": temp_expires,
                },
                actor,
            ) or created
            try:
                config = resolve_default_smtp()
                text, html = build_provisional_access_email(
                    display_name=created.display_name or created.name,
                    login=created.login,
                    provisional_password=plain_password,
                )
                send_plain_email(
                    config=config,
                    subject="Portal BI — senha provisória",
                    body=text,
                    html_body=html,
                    to_emails=[login_email],
                )
            except OutboundMailError as exc:
                raise UserServiceError(
                    f"Usuário criado, mas falha no envio de e-mail: {exc}"
                ) from exc
            audit_access_event(
                "provisional_password_on_create",
                actor=actor,
                target_user_id=int(created.id),
            )
        else:
            audit_access_event("user_created", actor=actor, target_user_id=int(created.id) if created.id else None)
        return created

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
            try:
                validate_password_policy(data.password)
            except ValueError as exc:
                raise UserServiceError(str(exc)) from exc
            fields["password_hash"] = hash_password(data.password)
            fields["must_change_password"] = False
            fields["temporary_password_expires_at"] = None

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

        if data.login_email is not None:
            try:
                login_email = validate_login_email(data.login_email)
            except ValueError as exc:
                raise UserServiceError(str(exc)) from exc
            if login_email:
                other = self._users.get_by_login_email(login_email, include_disabled=True)
                if other and other.id != user_id:
                    raise UserServiceError("Já existe um usuário com este e-mail de login.")
            fields["login_email"] = login_email

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

    def set_password_admin(
        self,
        user_id: int,
        *,
        password: Optional[str],
        generate: bool,
        actor: str,
    ) -> tuple[User, Optional[str]]:
        """Set password as admin. Returns (user, plaintext_if_generated)."""
        current = self._users.get_by_id(user_id, include_disabled=True)
        if current is None:
            raise UserServiceError("Usuário não encontrado.")
        plain: Optional[str] = None
        if generate:
            plain = generate_secure_password()
            password = plain
        if not password:
            raise UserServiceError("Informe a nova senha ou solicite geração automática.")
        try:
            validate_password_policy(password)
        except ValueError as exc:
            raise UserServiceError(str(exc)) from exc
        updated = self._users.update(
            user_id,
            {
                "password_hash": hash_password(password),
                "must_change_password": False,
                "temporary_password_expires_at": None,
            },
            actor,
        )
        if updated is None:
            raise UserServiceError("Falha ao alterar senha.")
        audit_access_event(
            "admin_set_password",
            actor=actor,
            target_user_id=user_id,
            detail="generated" if plain else "manual",
        )
        return updated, plain

    def change_own_password(
        self,
        user: User,
        *,
        current_password: str,
        new_password: str,
        confirm_password: str,
    ) -> User:
        if not current_password or not new_password:
            raise UserServiceError("Senha atual e nova senha são obrigatórias.")
        if new_password != confirm_password:
            raise UserServiceError("A confirmação não confere com a nova senha.")
        if not verify_password(current_password, user.password_hash):
            raise UserServiceError("Senha atual incorreta.")
        try:
            validate_password_policy(new_password)
        except ValueError as exc:
            raise UserServiceError(str(exc)) from exc
        if verify_password(new_password, user.password_hash):
            raise UserServiceError("A nova senha deve ser diferente da senha atual.")
        assert user.id is not None
        updated = self._users.update(
            int(user.id),
            {
                "password_hash": hash_password(new_password),
                "must_change_password": False,
                "temporary_password_expires_at": None,
            },
            user.login,
        )
        if updated is None:
            raise UserServiceError("Falha ao alterar senha.")
        audit_access_event("self_change_password", actor=user.login, target_user_id=int(user.id))
        return updated

    def send_provisional_password(self, user_id: int, actor: str) -> User:
        current = self._users.get_by_id(user_id, include_disabled=True)
        if current is None:
            raise UserServiceError("Usuário não encontrado.")
        if not (current.login_email or "").strip():
            raise UserServiceError(
                "O usuário não possui e-mail de login cadastrado. "
                "Cadastre um e-mail antes de enviar a senha provisória."
            )
        plain = generate_secure_password()
        expires = datetime.now(timezone.utc) + timedelta(hours=PROVISIONAL_PASSWORD_HOURS)
        updated = self._users.update(
            user_id,
            {
                "password_hash": hash_password(plain),
                "must_change_password": True,
                "temporary_password_expires_at": expires,
            },
            actor,
        )
        if updated is None:
            raise UserServiceError("Falha ao gerar senha provisória.")

        text, html = build_provisional_access_email(
            display_name=current.display_name or current.name,
            login=current.login,
            provisional_password=plain,
        )
        try:
            config = resolve_default_smtp()
            send_plain_email(
                config=config,
                subject="Portal BI — senha provisória",
                body=text,
                html_body=html,
                to_emails=[current.login_email.strip().lower()],
            )
        except OutboundMailError as exc:
            raise UserServiceError(f"Senha gerada, mas falha no envio de e-mail: {exc}") from exc
        audit_access_event(
            "provisional_password_sent",
            actor=actor,
            target_user_id=user_id,
        )
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
