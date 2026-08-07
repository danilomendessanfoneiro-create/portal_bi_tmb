"""Normalize and validate Brazilian CNPJ (14 digits + check digits)."""

from __future__ import annotations

import re

_DIGITS_RE = re.compile(r"\D+")


def normalize_cnpj(raw: str | None) -> str:
    return _DIGITS_RE.sub("", (raw or "").strip())


def _check_digit(digits: str, weights: list[int]) -> int:
    total = sum(int(d) * w for d, w in zip(digits, weights))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


def is_valid_cnpj(raw: str | None) -> bool:
    cnpj = normalize_cnpj(raw)
    if len(cnpj) != 14 or not cnpj.isdigit():
        return False
    if cnpj == cnpj[0] * 14:
        return False
    d1 = _check_digit(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = _check_digit(cnpj[:12] + str(d1), [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return cnpj[-2:] == f"{d1}{d2}"
