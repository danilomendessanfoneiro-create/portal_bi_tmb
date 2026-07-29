from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SmtpSettings:
    id: Optional[int]
    name: str
    host: str
    port: int
    username: str
    password_encrypted: str
    use_tls: bool
    sender_email: str
    sender_name: str
    timeout_seconds: Optional[int] = None
    is_default: bool = False
    created_by: Optional[str] = None
    created_on: Optional[datetime] = None
    modified_by: Optional[str] = None
    modified_on: Optional[datetime] = None
    enabled: bool = True


@dataclass
class EmailRecipient:
    id: Optional[int]
    name: str
    email: str
    role_title: Optional[str] = None
    department: Optional[str] = None
    receive_daily: bool = True
    receive_weekly: bool = False
    receive_monthly: bool = False
    created_by: Optional[str] = None
    created_on: Optional[datetime] = None
    modified_by: Optional[str] = None
    modified_on: Optional[datetime] = None
    enabled: bool = True
