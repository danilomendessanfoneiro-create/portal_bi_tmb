"""Orchestrates TMS Elite fetch + map (no persistence)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.integrations.tmselite.client import TmsEliteClient
from app.integrations.tmselite.exceptions import TmsEliteMappingError
from app.integrations.tmselite.mapper import map_delivery_item
from app.integrations.tmselite.models import DeliveryRecord

logger = logging.getLogger("tmselite.service")


@dataclass
class ImportFetchResult:
    records: list[DeliveryRecord]
    pages_processed: int
    error_count: int
    errors: list[str]


class TmsEliteIntegrationService:
    def __init__(self, client: TmsEliteClient) -> None:
        self._client = client

    def fetch_mapped(
        self,
        *,
        data_inicio: date,
        data_fim: date,
        id_status: Optional[str] = None,
        id_servico: Optional[str] = None,
    ) -> ImportFetchResult:
        records: list[DeliveryRecord] = []
        errors: list[str] = []
        pages = 0
        for page in self._client.iter_all_pages(
            data_inicio=data_inicio,
            data_fim=data_fim,
            id_status=id_status,
            id_servico=id_servico,
        ):
            pages += 1
            for item in page.items:
                try:
                    records.append(map_delivery_item(item))
                except TmsEliteMappingError as exc:
                    errors.append(str(exc))
                    logger.warning("Skip item: %s", exc)
        return ImportFetchResult(
            records=records,
            pages_processed=pages,
            error_count=len(errors),
            errors=errors[:50],
        )
