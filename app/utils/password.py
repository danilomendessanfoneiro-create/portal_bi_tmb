"""Password hashing and secure generation utilities."""

from __future__ import annotations

import hashlib
import secrets
import string

from app.config import settings

PASSWORD_MIN_LENGTH = 12
_UPPER = string.ascii_uppercase
_LOWER = string.ascii_lowercase
_DIGITS = string.digits
_SPECIAL = "!@#$%&*+-_=?"
_ALL = _UPPER + _LOWER + _DIGITS + _SPECIAL


def hash_password(password: str) -> str:
    return hashlib.sha256(
        f"{settings.password_salt}:{password}".encode("utf-8")
    ).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def validate_password_policy(password: str) -> None:
    """Raise ValueError if password does not meet complexity policy."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"A senha deve ter no mínimo {PASSWORD_MIN_LENGTH} caracteres."
        )
    if not any(c in _UPPER for c in password):
        raise ValueError("A senha deve conter ao menos uma letra maiúscula.")
    if not any(c in _LOWER for c in password):
        raise ValueError("A senha deve conter ao menos uma letra minúscula.")
    if not any(c in _DIGITS for c in password):
        raise ValueError("A senha deve conter ao menos um número.")
    if not any(c in _SPECIAL for c in password):
        raise ValueError("A senha deve conter ao menos um caractere especial.")


def generate_secure_password(length: int = PASSWORD_MIN_LENGTH) -> str:
    """Generate a cryptographically secure password meeting policy."""
    if length < PASSWORD_MIN_LENGTH:
        length = PASSWORD_MIN_LENGTH
    chars = [
        secrets.choice(_UPPER),
        secrets.choice(_LOWER),
        secrets.choice(_DIGITS),
        secrets.choice(_SPECIAL),
    ]
    chars.extend(secrets.choice(_ALL) for _ in range(length - 4))
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    password = "".join(chars)
    validate_password_policy(password)
    return password
