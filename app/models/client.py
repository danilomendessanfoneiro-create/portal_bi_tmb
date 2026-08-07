from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Client:
    id: Optional[int]
    name: str
    cnpj: str
    emails: Optional[str] = None
    created_by: Optional[str] = None
    created_on: Optional[datetime] = None
    modified_by: Optional[str] = None
    modified_on: Optional[datetime] = None
    enabled: bool = True
