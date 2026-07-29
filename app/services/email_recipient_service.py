"""Email recipients business rules."""

from __future__ import annotations

import re
from typing import Optional

from app.models.settings_models import EmailRecipient
from app.repositories.email_recipient_repository import EmailRecipientRepository
from app.schemas.settings import RecipientCreate, RecipientFilter, RecipientUpdate

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RecipientServiceError(Exception):
    pass


class EmailRecipientService:
    def __init__(self, repo: Optional[EmailRecipientRepository] = None) -> None:
        self._repo = repo or EmailRecipientRepository()

    def get(self, item_id: int) -> Optional[EmailRecipient]:
        return self._repo.get_by_id(item_id, include_disabled=True)

    def list(self, filters: RecipientFilter) -> tuple[list[EmailRecipient], int]:
        return self._repo.list(filters)

    def list_for_report(self, period: str) -> list[EmailRecipient]:
        return self._repo.list_active_for_report(period)

    def create(self, data: RecipientCreate, actor: str) -> EmailRecipient:
        name = (data.name or "").strip()
        email = (data.email or "").strip().lower()
        if not name:
            raise RecipientServiceError("Nome é obrigatório.")
        if not EMAIL_RE.match(email):
            raise RecipientServiceError("E-mail inválido.")
        if self._repo.get_by_email(email, include_disabled=True):
            raise RecipientServiceError("Já existe destinatário com este e-mail.")
        return self._repo.insert(
            data={
                "name": name,
                "email": email,
                "role_title": (data.role_title or "").strip() or None,
                "department": (data.department or "").strip() or None,
                "receive_daily": bool(data.receive_daily),
                "receive_weekly": bool(data.receive_weekly),
                "receive_monthly": bool(data.receive_monthly),
                "enabled": bool(data.enabled),
            },
            actor=actor,
        )

    def update(self, item_id: int, data: RecipientUpdate, actor: str) -> EmailRecipient:
        current = self._repo.get_by_id(item_id, include_disabled=True)
        if current is None:
            raise RecipientServiceError("Destinatário não encontrado.")

        fields: dict = {}
        if data.name is not None:
            name = data.name.strip()
            if not name:
                raise RecipientServiceError("Nome é obrigatório.")
            fields["name"] = name
        if data.email is not None:
            email = data.email.strip().lower()
            if not EMAIL_RE.match(email):
                raise RecipientServiceError("E-mail inválido.")
            other = self._repo.get_by_email(email, include_disabled=True)
            if other and other.id != item_id:
                raise RecipientServiceError("Já existe destinatário com este e-mail.")
            fields["email"] = email
        if data.role_title is not None:
            fields["role_title"] = data.role_title.strip() or None
        if data.department is not None:
            fields["department"] = data.department.strip() or None
        if data.receive_daily is not None:
            fields["receive_daily"] = bool(data.receive_daily)
        if data.receive_weekly is not None:
            fields["receive_weekly"] = bool(data.receive_weekly)
        if data.receive_monthly is not None:
            fields["receive_monthly"] = bool(data.receive_monthly)
        if data.enabled is not None:
            fields["enabled"] = bool(data.enabled)

        updated = self._repo.update(item_id, fields, actor)
        if updated is None:
            raise RecipientServiceError("Falha ao atualizar destinatário.")
        return updated

    def soft_delete(self, item_id: int, actor: str) -> EmailRecipient:
        current = self._repo.get_by_id(item_id, include_disabled=True)
        if current is None:
            raise RecipientServiceError("Destinatário não encontrado.")
        updated = self._repo.soft_delete(item_id, actor)
        if updated is None:
            raise RecipientServiceError("Falha ao desativar destinatário.")
        return updated
