"""US-005: secure password generation and policy."""

from __future__ import annotations

import string

import pytest

from app.utils.password import (
    PASSWORD_MIN_LENGTH,
    generate_secure_password,
    validate_password_policy,
)

_SPECIAL = "!@#$%&*+-_=?"


def test_generate_secure_password_meets_policy():
    for _ in range(40):
        pwd = generate_secure_password()
        assert len(pwd) >= PASSWORD_MIN_LENGTH
        assert any(c in string.ascii_uppercase for c in pwd)
        assert any(c in string.ascii_lowercase for c in pwd)
        assert any(c in string.digits for c in pwd)
        assert any(c in _SPECIAL for c in pwd)
        validate_password_policy(pwd)


def test_generate_secure_password_custom_length():
    pwd = generate_secure_password(20)
    assert len(pwd) == 20
    validate_password_policy(pwd)


def test_validate_password_policy_rejects_weak():
    with pytest.raises(ValueError, match="mínimo"):
        validate_password_policy("Aa1!")
    with pytest.raises(ValueError, match="maiúscula"):
        validate_password_policy("abcdefghi1!x")
    with pytest.raises(ValueError, match="minúscula"):
        validate_password_policy("ABCDEFGHI1!X")
    with pytest.raises(ValueError, match="número"):
        validate_password_policy("Abcdefghi!xx")
    with pytest.raises(ValueError, match="especial"):
        validate_password_policy("Abcdefghi12x")
