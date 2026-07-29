"""Runtime context, logging helpers, and job result types."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from app.config import settings

TZ_SP = ZoneInfo("America/Sao_Paulo")


@dataclass
class JobContext:
    job_id: str
    business_date: date
    force: bool = False
    dry_run: bool = False
    if_due: bool = False
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("worker"))

    @property
    def data_csv(self) -> Path:
        return settings.data_csv

    @property
    def reports_dir(self) -> Path:
        path = settings.root_dir / "storage" / "reports" / self.business_date.isoformat()
        path.mkdir(parents=True, exist_ok=True)
        return path


@dataclass
class JobResult:
    status: str  # success | failed | skipped
    message: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    artifact_path: Optional[Path] = None


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("worker")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def today_sp() -> date:
    return datetime.now(TZ_SP).date()


def parse_business_date(value: Optional[str]) -> date:
    if not value:
        return today_sp()
    return date.fromisoformat(value)
