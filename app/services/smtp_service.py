"""SMTP settings business rules."""

from __future__ import annotations

import re
from typing import Optional

from app.models.settings_models import SmtpSettings
from app.repositories.smtp_repository import SmtpSettingsRepository
from app.schemas.settings import SmtpCreate, SmtpFilter, SmtpUpdate
from app.utils.secret_box import decrypt_secret, encrypt_secret

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SmtpServiceError(Exception):
    pass


class SmtpSettingsService:
    def __init__(self, repo: Optional[SmtpSettingsRepository] = None) -> None:
        self._repo = repo or SmtpSettingsRepository()

    def get(self, item_id: int) -> Optional[SmtpSettings]:
        return self._repo.get_by_id(item_id, include_disabled=True)

    def get_default(self) -> Optional[SmtpSettings]:
        return self._repo.get_default()

    def get_default_password(self) -> Optional[str]:
        item = self.get_default()
        if item is None:
            return None
        return decrypt_secret(item.password_encrypted)

    def list(self, filters: SmtpFilter) -> tuple[list[SmtpSettings], int]:
        return self._repo.list(filters)

    def create(self, data: SmtpCreate, actor: str) -> SmtpSettings:
        self._validate(data.name, data.host, data.port, data.username, data.password, data.sender_email, data.sender_name)
        if data.is_default:
            self._repo.clear_default()
        return self._repo.insert(
            data={
                "name": data.name.strip(),
                "host": data.host.strip(),
                "port": int(data.port),
                "username": data.username.strip(),
                "password_encrypted": encrypt_secret(data.password),
                "use_tls": bool(data.use_tls),
                "sender_email": data.sender_email.strip(),
                "sender_name": data.sender_name.strip(),
                "timeout_seconds": data.timeout_seconds,
                "is_default": bool(data.is_default),
                "enabled": bool(data.enabled),
            },
            actor=actor,
        )

    def update(self, item_id: int, data: SmtpUpdate, actor: str) -> SmtpSettings:
        current = self._repo.get_by_id(item_id, include_disabled=True)
        if current is None:
            raise SmtpServiceError("Configuração SMTP não encontrada.")

        fields: dict = {}
        if data.name is not None:
            name = data.name.strip()
            if not name:
                raise SmtpServiceError("Nome da configuração é obrigatório.")
            fields["name"] = name
        if data.host is not None:
            host = data.host.strip()
            if not host:
                raise SmtpServiceError("Host SMTP é obrigatório.")
            fields["host"] = host
        if data.port is not None:
            if data.port <= 0 or data.port > 65535:
                raise SmtpServiceError("Porta SMTP inválida.")
            fields["port"] = int(data.port)
        if data.username is not None:
            username = data.username.strip()
            if not username:
                raise SmtpServiceError("Usuário SMTP é obrigatório.")
            fields["username"] = username
        if data.password:
            fields["password_encrypted"] = encrypt_secret(data.password)
        if data.use_tls is not None:
            fields["use_tls"] = bool(data.use_tls)
        if data.sender_email is not None:
            email = data.sender_email.strip()
            if not EMAIL_RE.match(email):
                raise SmtpServiceError("E-mail do remetente inválido.")
            fields["sender_email"] = email
        if data.sender_name is not None:
            sname = data.sender_name.strip()
            if not sname:
                raise SmtpServiceError("Nome do remetente é obrigatório.")
            fields["sender_name"] = sname
        if data.timeout_seconds is not None:
            fields["timeout_seconds"] = data.timeout_seconds
        if data.enabled is not None:
            fields["enabled"] = bool(data.enabled)
            if not data.enabled:
                fields["is_default"] = False
        if data.is_default is not None:
            fields["is_default"] = bool(data.is_default)

        becoming_default = fields.get("is_default", current.is_default)
        still_enabled = fields.get("enabled", current.enabled)
        if becoming_default and still_enabled:
            self._repo.clear_default(except_id=item_id)
            fields["is_default"] = True

        updated = self._repo.update(item_id, fields, actor)
        if updated is None:
            raise SmtpServiceError("Falha ao atualizar configuração SMTP.")
        return updated

    def soft_delete(self, item_id: int, actor: str) -> SmtpSettings:
        current = self._repo.get_by_id(item_id, include_disabled=True)
        if current is None:
            raise SmtpServiceError("Configuração SMTP não encontrada.")
        updated = self._repo.soft_delete(item_id, actor)
        if updated is None:
            raise SmtpServiceError("Falha ao desativar configuração SMTP.")
        return updated

    def _validate(
        self,
        name: str,
        host: str,
        port: int,
        username: str,
        password: str,
        sender_email: str,
        sender_name: str,
    ) -> None:
        if not (name or "").strip():
            raise SmtpServiceError("Nome da configuração é obrigatório.")
        if not (host or "").strip():
            raise SmtpServiceError("Host SMTP é obrigatório.")
        if port is None or port <= 0 or port > 65535:
            raise SmtpServiceError("Porta SMTP inválida.")
        if not (username or "").strip():
            raise SmtpServiceError("Usuário SMTP é obrigatório.")
        if not password:
            raise SmtpServiceError("Senha SMTP é obrigatória.")
        if not EMAIL_RE.match((sender_email or "").strip()):
            raise SmtpServiceError("E-mail do remetente inválido.")
        if not (sender_name or "").strip():
            raise SmtpServiceError("Nome do remetente é obrigatório.")
