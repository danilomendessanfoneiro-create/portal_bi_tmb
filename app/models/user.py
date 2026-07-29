from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: Optional[int]
    login: str
    password_hash: str
    profile: str
    branch: Optional[str]
    display_name: Optional[str]
    name: Optional[str]
    code: Optional[str]
    report_emails: Optional[str] = None
    created_by: Optional[str] = None
    created_on: Optional[datetime] = None
    modified_by: Optional[str] = None
    modified_on: Optional[datetime] = None
    enabled: bool = True

    @property
    def is_admin(self) -> bool:
        return (self.profile or "").lower() == "admin"
