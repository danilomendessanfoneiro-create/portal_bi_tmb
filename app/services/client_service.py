"""Clients business rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientFilter, ClientUpdate
from app.services.email_recipient_service import EMAIL_RE
from app.utils.cnpj import is_valid_cnpj, normalize_cnpj
from app.utils.report_emails import parse_report_emails

try:
    from psycopg.errors import IntegrityError, UniqueViolation
except ImportError:  # pragma: no cover
    UniqueViolation = type("UniqueViolation", (Exception,), {})  # type: ignore[misc,assignment]
    IntegrityError = UniqueViolation  # type: ignore[misc,assignment]


class ClientServiceError(Exception):
    pass


@dataclass(frozen=True)
class ClientReportTarget:
    id: int
    name: str
    cnpj: str
    emails_raw: Optional[str]

    @property
    def emails(self) -> list[str]:
        return parse_client_emails(self.emails_raw)


def parse_client_emails(raw: str | None) -> list[str]:
    """Aceita vírgula (CRUD Clientes) ou ponto-e-vírgula (padrão filiais)."""
    if not raw or not str(raw).strip():
        return []
    normalized = str(raw).replace(",", ";")
    return parse_report_emails(normalized)


def normalize_client_emails(raw: str | None) -> Optional[str]:
    if raw is None or not str(raw).strip():
        return None
    parts = [p.strip().lower() for p in str(raw).split(",") if p.strip()]
    if not parts:
        return None
    return ",".join(parts)


def validate_client_emails(raw: str | None) -> Optional[str]:
    if raw is None or not str(raw).strip():
        return None
    # Aceita vírgula ou ponto-e-vírgula como separador
    normalized_raw = str(raw).replace(";", ",")
    parts = [p.strip() for p in normalized_raw.split(",") if p.strip()]
    seen: set[str] = set()
    normalized: list[str] = []
    for email in parts:
        lower = email.lower()
        if not EMAIL_RE.match(lower):
            raise ClientServiceError(f"E-mail inválido: {email}")
        if lower in seen:
            raise ClientServiceError(f"E-mail duplicado: {email}")
        seen.add(lower)
        normalized.append(lower)
    return ",".join(normalized) if normalized else None


class ClientService:
    def __init__(self, repo: Optional[ClientRepository] = None) -> None:
        self._repo = repo or ClientRepository()

    def get(self, item_id: int) -> Optional[Client]:
        return self._repo.get_by_id(item_id, include_disabled=True)

    def list(self, filters: ClientFilter) -> tuple[list[Client], int]:
        return self._repo.list(filters)

    def list_for_reports(self) -> list[ClientReportTarget]:
        out: list[ClientReportTarget] = []
        for row in self._repo.list_enabled():
            cnpj = str(row.get("cnpj") or "").strip()
            if not cnpj:
                continue
            out.append(
                ClientReportTarget(
                    id=int(row["id"]),
                    name=str(row.get("name") or cnpj).strip(),
                    cnpj=cnpj,
                    emails_raw=row.get("emails"),
                )
            )
        return out

    def _require_valid_cnpj(self, raw: str) -> str:
        cnpj = normalize_cnpj(raw)
        if not is_valid_cnpj(cnpj):
            raise ClientServiceError("CNPJ inválido.")
        return cnpj

    def create(self, data: ClientCreate, actor: str) -> Client:
        name = (data.name or "").strip()
        if not name:
            raise ClientServiceError("Nome é obrigatório.")
        cnpj = self._require_valid_cnpj(data.cnpj)
        if self._repo.get_enabled_by_cnpj(cnpj):
            raise ClientServiceError("Já existe cliente ativo com este CNPJ.")
        emails = validate_client_emails(data.emails)
        try:
            return self._repo.insert(
                data={
                    "name": name,
                    "cnpj": cnpj,
                    "emails": emails,
                    "enabled": bool(data.enabled),
                },
                actor=actor,
            )
        except (UniqueViolation, IntegrityError) as exc:
            raise ClientServiceError("Já existe cliente ativo com este CNPJ.") from exc

    def update(self, item_id: int, data: ClientUpdate, actor: str) -> Client:
        current = self._repo.get_by_id(item_id, include_disabled=True)
        if current is None:
            raise ClientServiceError("Cliente não encontrado.")

        fields: dict = {}
        if data.name is not None:
            name = data.name.strip()
            if not name:
                raise ClientServiceError("Nome é obrigatório.")
            fields["name"] = name
        if data.cnpj is not None:
            cnpj = self._require_valid_cnpj(data.cnpj)
            other = self._repo.get_enabled_by_cnpj(cnpj, exclude_id=item_id)
            if other:
                raise ClientServiceError("Já existe cliente ativo com este CNPJ.")
            fields["cnpj"] = cnpj
        if data.emails is not None:
            # String vazia limpa os e-mails no update
            raw_emails = data.emails.strip() if isinstance(data.emails, str) else data.emails
            fields["emails"] = validate_client_emails(raw_emails or None)
        if data.enabled is not None:
            enabled = bool(data.enabled)
            if enabled:
                cnpj = fields.get("cnpj", current.cnpj)
                other = self._repo.get_enabled_by_cnpj(cnpj, exclude_id=item_id)
                if other:
                    raise ClientServiceError("Já existe cliente ativo com este CNPJ.")
            fields["enabled"] = enabled

        try:
            updated = self._repo.update(item_id, fields, actor)
        except (UniqueViolation, IntegrityError) as exc:
            raise ClientServiceError("Já existe cliente ativo com este CNPJ.") from exc
        if updated is None:
            raise ClientServiceError("Falha ao atualizar cliente.")
        return updated

    def soft_delete(self, item_id: int, actor: str) -> Client:
        current = self._repo.get_by_id(item_id, include_disabled=True)
        if current is None:
            raise ClientServiceError("Cliente não encontrado.")
        updated = self._repo.soft_delete(item_id, actor)
        if updated is None:
            raise ClientServiceError("Falha ao desativar cliente.")
        return updated

    def upsert_from_seed(self, *, name: str, cnpj_raw: str, actor: str) -> tuple[Client, str]:
        name = (name or "").strip()
        if not name:
            raise ClientServiceError("Nome é obrigatório.")
        cnpj = self._require_valid_cnpj(cnpj_raw)
        return self._repo.upsert_by_cnpj(name=name, cnpj=cnpj, actor=actor)
