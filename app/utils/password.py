"""Password hashing utilities (compatible with legacy usuarios.csv)."""

from __future__ import annotations

import hashlib

from app.config import settings


def hash_password(password: str) -> str:
    return hashlib.sha256(
        f"{settings.password_salt}:{password}".encode("utf-8")
    ).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash
