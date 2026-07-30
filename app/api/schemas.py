"""Pydantic schemas for the REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    login: str
    profile: str
    branch: Optional[str] = None
    display_name: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    report_emails: Optional[str] = None
    enabled: bool = True
    created_on: Optional[datetime] = None
    modified_on: Optional[datetime] = None


class UserCreateBody(BaseModel):
    login: str
    password: str
    profile: str = "filial"
    branch: Optional[str] = None
    display_name: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    report_emails: Optional[str] = None
    enabled: bool = True


class UserUpdateBody(BaseModel):
    login: Optional[str] = None
    password: Optional[str] = None
    profile: Optional[str] = None
    branch: Optional[str] = None
    display_name: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    report_emails: Optional[str] = None
    enabled: Optional[bool] = None


class UserListResponse(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class MessageOut(BaseModel):
    detail: str


class SmtpOut(BaseModel):
    id: int
    name: str
    host: str
    port: int
    username: str
    use_tls: bool
    sender_email: str
    sender_name: str
    timeout_seconds: Optional[int] = None
    is_default: bool = False
    enabled: bool = True
    created_on: Optional[datetime] = None
    modified_on: Optional[datetime] = None


class SmtpCreateBody(BaseModel):
    name: str
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True
    sender_email: str
    sender_name: str
    timeout_seconds: Optional[int] = None
    is_default: bool = False
    enabled: bool = True


class SmtpUpdateBody(BaseModel):
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


class SmtpListResponse(BaseModel):
    items: list[SmtpOut]
    total: int
    page: int
    page_size: int


class RecipientOut(BaseModel):
    id: int
    name: str
    email: str
    role_title: Optional[str] = None
    department: Optional[str] = None
    receive_daily: bool = True
    receive_weekly: bool = False
    receive_monthly: bool = False
    enabled: bool = True
    created_on: Optional[datetime] = None
    modified_on: Optional[datetime] = None


class RecipientCreateBody(BaseModel):
    name: str
    email: str
    role_title: Optional[str] = None
    department: Optional[str] = None
    receive_daily: bool = True
    receive_weekly: bool = False
    receive_monthly: bool = False
    enabled: bool = True


class RecipientUpdateBody(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role_title: Optional[str] = None
    department: Optional[str] = None
    receive_daily: Optional[bool] = None
    receive_weekly: Optional[bool] = None
    receive_monthly: Optional[bool] = None
    enabled: Optional[bool] = None


class RecipientListResponse(BaseModel):
    items: list[RecipientOut]
    total: int
    page: int
    page_size: int


class ApiSettingsOut(BaseModel):
    id: int
    name: str
    base_url: str
    endpoint: str
    timeout_seconds: int = 60
    page_size: int = 500
    initial_load_days: int = 90
    is_default: bool = False
    enabled: bool = True
    has_token: bool = True
    created_on: Optional[datetime] = None
    modified_on: Optional[datetime] = None


class ApiSettingsCreateBody(BaseModel):
    name: str
    base_url: str
    endpoint: str
    token: str
    timeout_seconds: int = 60
    page_size: int = 500
    initial_load_days: int = 90
    is_default: bool = False
    enabled: bool = True


class ApiSettingsUpdateBody(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    endpoint: Optional[str] = None
    token: Optional[str] = None
    timeout_seconds: Optional[int] = None
    page_size: Optional[int] = None
    initial_load_days: Optional[int] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None


class ApiSettingsListResponse(BaseModel):
    items: list[ApiSettingsOut]
    total: int
    page: int
    page_size: int


class ImportBatchOut(BaseModel):
    id: int
    file_name: str
    file_ext: str
    file_size_bytes: int
    file_mtime: Optional[datetime] = None
    status: str
    total_rows: int = 0
    valid_rows: int = 0
    error_rows: int = 0
    rows_processed: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    progress_pct: float = 0
    validation_errors: list[dict] = []
    started_on: Optional[datetime] = None
    finished_on: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    report_job_status: Optional[str] = None
    report_job_message: Optional[str] = None
    created_by: Optional[str] = None
    created_on: Optional[datetime] = None


class ImportBatchListResponse(BaseModel):
    items: list[ImportBatchOut]
    total: int
    page: int
    page_size: int


class ImportErrorOut(BaseModel):
    row_number: Optional[int] = None
    level: str = "error"
    message: str


TokenResponse.model_rebuild()
