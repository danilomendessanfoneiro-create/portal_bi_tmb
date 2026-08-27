"""Normalize and validate a single login e-mail."""

from __future__ import annotations

from app.services.email_recipient_service import EMAIL_RE


def normalize_login_email(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    return value.lower()


def validate_login_email(raw: str | None) -> str | None:
    """Return normalized e-mail or None if empty; raise ValueError if invalid."""
    normalized = normalize_login_email(raw)
    if normalized is None:
        return None
    if not EMAIL_RE.match(normalized):
        raise ValueError(f"E-mail de login inválido: {raw}")
    return normalized
