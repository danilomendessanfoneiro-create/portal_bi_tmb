from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SmtpCreate:
    name: str
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True
    sender_email: str = ""
    sender_name: str = ""
    timeout_seconds: Optional[int] = None
    is_default: bool = False
    enabled: bool = True


@dataclass
class SmtpUpdate:
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: Optional[bool] = None
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    timeout_seconds: Optional[int] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None


@dataclass
class SmtpFilter:
    search: Optional[str] = None
    enabled: Optional[bool] = True
    page: int = 1
    page_size: int = 10
    sort_by: str = "name"
    sort_dir: str = "asc"


@dataclass
class RecipientCreate:
    name: str
    email: str
    role_title: Optional[str] = None
    department: Optional[str] = None
    receive_daily: bool = True
    receive_weekly: bool = False
    receive_monthly: bool = False
    enabled: bool = True


@dataclass
class RecipientUpdate:
    name: Optional[str] = None
    email: Optional[str] = None
    role_title: Optional[str] = None
    department: Optional[str] = None
    receive_daily: Optional[bool] = None
    receive_weekly: Optional[bool] = None
    receive_monthly: Optional[bool] = None
    enabled: Optional[bool] = None


@dataclass
class RecipientFilter:
    search: Optional[str] = None
    enabled: Optional[bool] = True
    page: int = 1
    page_size: int = 10
    sort_by: str = "name"
    sort_dir: str = "asc"


@dataclass
class ApiSettingsCreate:
    name: str
    base_url: str
    endpoint: str
    token: str
    timeout_seconds: int = 60
    page_size: int = 500
    initial_load_days: int = 90
    is_default: bool = False
    enabled: bool = True


@dataclass
class ApiSettingsUpdate:
    name: Optional[str] = None
    base_url: Optional[str] = None
    endpoint: Optional[str] = None
    token: Optional[str] = None
    timeout_seconds: Optional[int] = None
    page_size: Optional[int] = None
    initial_load_days: Optional[int] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None


@dataclass
class ApiSettingsFilter:
    search: Optional[str] = None
    enabled: Optional[bool] = True
    page: int = 1
    page_size: int = 10
    sort_by: str = "name"
    sort_dir: str = "asc"
