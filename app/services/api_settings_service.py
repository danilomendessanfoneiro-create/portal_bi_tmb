"""API settings business rules."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from app.models.settings_models import ApiSettings
from app.repositories.api_settings_repository import ApiSettingsRepository
from app.schemas.settings import ApiSettingsCreate, ApiSettingsFilter, ApiSettingsUpdate
from app.utils.secret_box import decrypt_secret, encrypt_secret


def normalize_bearer_token(token: str) -> str:
    value = (token or "").strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    return value


class ApiSettingsServiceError(Exception):
    pass


class ApiSettingsService:
    def __init__(self, repo: Optional[ApiSettingsRepository] = None) -> None:
        self._repo = repo or ApiSettingsRepository()

    def get(self, item_id: int) -> Optional[ApiSettings]:
        return self._repo.get_by_id(item_id, include_disabled=True)

    def get_default(self) -> Optional[ApiSettings]:
        return self._repo.get_default()

    def get_default_token(self) -> Optional[str]:
        item = self.get_default()
        if item is None:
            return None
        return decrypt_secret(item.token_encrypted)

    def list(self, filters: ApiSettingsFilter) -> tuple[list[ApiSettings], int]:
        return self._repo.list(filters)

    def create(self, data: ApiSettingsCreate, actor: str) -> ApiSettings:
        self._validate(
            data.name,
            data.base_url,
            data.endpoint,
            data.token,
            data.timeout_seconds,
            data.page_size,
            data.initial_load_days,
        )
        if data.is_default:
            self._repo.clear_default()
        token = normalize_bearer_token(data.token)
        return self._repo.insert(
            data={
                "name": data.name.strip(),
                "base_url": data.base_url.strip().rstrip("/"),
                "endpoint": data.endpoint.strip(),
                "token_encrypted": encrypt_secret(token),
                "timeout_seconds": int(data.timeout_seconds),
                "page_size": int(data.page_size),
                "initial_load_days": int(data.initial_load_days),
                "is_default": bool(data.is_default),
                "enabled": bool(data.enabled),
            },
            actor=actor,
        )

    def update(self, item_id: int, data: ApiSettingsUpdate, actor: str) -> ApiSettings:
        current = self._repo.get_by_id(item_id, include_disabled=True)
        if current is None:
            raise ApiSettingsServiceError("Configuração de API não encontrada.")

        fields: dict = {}
        if data.name is not None:
            name = data.name.strip()
            if not name:
                raise ApiSettingsServiceError("Nome é obrigatório.")
            fields["name"] = name
        if data.base_url is not None:
            base = data.base_url.strip().rstrip("/")
            self._validate_url(base)
            fields["base_url"] = base
        if data.endpoint is not None:
            endpoint = data.endpoint.strip()
            if not endpoint:
                raise ApiSettingsServiceError("Endpoint é obrigatório.")
            fields["endpoint"] = endpoint
        if data.token:
            fields["token_encrypted"] = encrypt_secret(normalize_bearer_token(data.token))
        if data.timeout_seconds is not None:
            if data.timeout_seconds <= 0 or data.timeout_seconds > 600:
                raise ApiSettingsServiceError("Timeout inválido.")
            fields["timeout_seconds"] = int(data.timeout_seconds)
        if data.page_size is not None:
            if data.page_size <= 0 or data.page_size > 5000:
                raise ApiSettingsServiceError("Page size inválido.")
            fields["page_size"] = int(data.page_size)
        if data.initial_load_days is not None:
            if data.initial_load_days <= 0 or data.initial_load_days > 3650:
                raise ApiSettingsServiceError("Dias de carga inicial inválidos.")
            fields["initial_load_days"] = int(data.initial_load_days)
        if data.enabled is not None:
            fields["enabled"] = bool(data.enabled)
        if data.is_default is not None:
            if data.is_default:
                self._repo.clear_default(except_id=item_id)
            fields["is_default"] = bool(data.is_default)

        updated = self._repo.update(item_id, fields, actor)
        if updated is None:
            raise ApiSettingsServiceError("Falha ao atualizar configuração.")
        return updated

    def soft_delete(self, item_id: int, actor: str) -> ApiSettings:
        updated = self._repo.soft_delete(item_id, actor)
        if updated is None:
            raise ApiSettingsServiceError("Configuração não encontrada.")
        return updated

    def _validate(
        self,
        name: str,
        base_url: str,
        endpoint: str,
        token: str,
        timeout_seconds: int,
        page_size: int,
        initial_load_days: int,
    ) -> None:
        if not (name or "").strip():
            raise ApiSettingsServiceError("Nome é obrigatório.")
        self._validate_url((base_url or "").strip())
        if not (endpoint or "").strip():
            raise ApiSettingsServiceError("Endpoint é obrigatório.")
        if not (token or "").strip():
            raise ApiSettingsServiceError("Token Bearer é obrigatório.")
        if timeout_seconds <= 0 or timeout_seconds > 600:
            raise ApiSettingsServiceError("Timeout inválido.")
        if page_size <= 0 or page_size > 5000:
            raise ApiSettingsServiceError("Page size inválido.")
        if initial_load_days <= 0 or initial_load_days > 3650:
            raise ApiSettingsServiceError("Dias de carga inicial inválidos.")

    @staticmethod
    def _validate_url(base_url: str) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ApiSettingsServiceError("URL base inválida.")
