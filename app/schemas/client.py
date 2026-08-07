from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ClientCreate:
    name: str
    cnpj: str
    emails: Optional[str] = None
    enabled: bool = True


@dataclass
class ClientUpdate:
    name: Optional[str] = None
    cnpj: Optional[str] = None
    emails: Optional[str] = None
    enabled: Optional[bool] = None


@dataclass
class ClientFilter:
    search: Optional[str] = None
    enabled: Optional[bool] = True
    page: int = 1
    page_size: int = 10
    sort_by: str = "name"
    sort_dir: str = "asc"
