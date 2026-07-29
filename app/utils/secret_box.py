"""Symmetric encryption for sensitive settings (e.g. SMTP password)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    digest = hashlib.sha256(
        f"{settings.jwt_secret}:{settings.password_salt}:smtp-box".encode("utf-8")
    ).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    if not plain:
        return plain
    if plain.startswith(PREFIX):
        return plain
    token = _fernet().encrypt(plain.encode("utf-8")).decode("ascii")
    return f"{PREFIX}{token}"


def decrypt_secret(stored: str) -> str:
    if not stored:
        return stored
    if not stored.startswith(PREFIX):
        return stored
    raw = stored[len(PREFIX) :]
    try:
        return _fernet().decrypt(raw.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Falha ao decifrar segredo armazenado.") from exc
