"""Validação e normalização de clientes (CNPJ / e-mails)."""

from __future__ import annotations

import pytest

from app.services.client_service import (
    ClientService,
    ClientServiceError,
    normalize_client_emails,
    parse_client_emails,
    validate_client_emails,
)
from app.utils.cnpj import is_valid_cnpj, normalize_cnpj

VALID_CNPJ = "07604556000136"
VALID_CNPJ_FMT = "07.604.556/0001-36"


def test_normalize_cnpj_digits_only():
    assert normalize_cnpj(VALID_CNPJ_FMT) == VALID_CNPJ
    assert normalize_cnpj(" 07.604.556/0001-36 ") == VALID_CNPJ
    assert normalize_cnpj(None) == ""


def test_is_valid_cnpj_check_digits():
    assert is_valid_cnpj(VALID_CNPJ) is True
    assert is_valid_cnpj(VALID_CNPJ_FMT) is True
    assert is_valid_cnpj("12345678901234") is False
    assert is_valid_cnpj("00000000000000") is False
    assert is_valid_cnpj("123") is False
    assert is_valid_cnpj("") is False


def test_normalize_client_emails_comma_separated():
    assert normalize_client_emails(None) is None
    assert normalize_client_emails("  ") is None
    assert normalize_client_emails("A@B.COM, c@d.com") == "a@b.com,c@d.com"


def test_validate_client_emails_ok_and_invalid():
    assert validate_client_emails("") is None
    assert validate_client_emails("a@b.com, c@d.com") == "a@b.com,c@d.com"
    with pytest.raises(ClientServiceError, match="inválido"):
        validate_client_emails("nao-email")
    with pytest.raises(ClientServiceError, match="duplicado"):
        validate_client_emails("a@b.com, A@B.com")


def test_parse_client_emails_accepts_comma_or_semicolon():
    assert parse_client_emails("a@b.com, c@d.com") == ["a@b.com", "c@d.com"]
    assert parse_client_emails("a@b.com; c@d.com") == ["a@b.com", "c@d.com"]


def test_service_require_valid_cnpj():
    svc = object.__new__(ClientService)
    assert svc._require_valid_cnpj(VALID_CNPJ_FMT) == VALID_CNPJ
    with pytest.raises(ClientServiceError, match="CNPJ inválido"):
        svc._require_valid_cnpj("11.111.111/1111-11")
