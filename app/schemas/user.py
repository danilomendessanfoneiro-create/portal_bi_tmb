from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserCreate:
    login: str
    password: str
    profile: str
    branch: Optional[str] = None
    display_name: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    report_emails: Optional[str] = None
    enabled: bool = True


@dataclass
class UserUpdate:
    login: Optional[str] = None
    password: Optional[str] = None
    profile: Optional[str] = None
    branch: Optional[str] = None
    display_name: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    report_emails: Optional[str] = None
    enabled: Optional[bool] = None


@dataclass
class UserFilter:
    search: Optional[str] = None
    profile: Optional[str] = None
    enabled: Optional[bool] = None
    page: int = 1
    page_size: int = 10
    sort_by: str = "login"
    sort_dir: str = "asc"
