"""Import deliveries from TMS Elite into prb_deliveries."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from app.integrations.tmselite.client import TmsEliteClient
from app.integrations.tmselite.exceptions import TmsEliteConfigError, TmsEliteError
from app.integrations.tmselite.service import TmsEliteIntegrationService
from app.repositories.delivery_repository import DeliveryRepository
from app.repositories.integration_log_repository import IntegrationLogRepository
from app.services.api_settings_service import ApiSettingsService
from app.utils.secret_box import decrypt_secret

logger = logging.getLogger("delivery_import")


@dataclass
class DeliveryImportResult:
    status: str
    message: str
    pages_processed: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    error_count: int = 0
    filter_start: Optional[date] = None
    filter_end: Optional[date] = None


class DeliveryImportService:
    def __init__(
        self,
        api_settings: Optional[ApiSettingsService] = None,
        deliveries: Optional[DeliveryRepository] = None,
        logs: Optional[IntegrationLogRepository] = None,
    ) -> None:
        self._api = api_settings or ApiSettingsService()
        self._deliveries = deliveries or DeliveryRepository()
        self._logs = logs or IntegrationLogRepository()

    def run_initial(
        self,
        *,
        business_date: date,
        dry_run: bool = False,
        actor: str = "worker",
        job_id: str = "import_deliveries_initial",
        initial_load_days: Optional[int] = None,
    ) -> DeliveryImportResult:
        cfg = self._require_config()
        days = int(initial_load_days) if initial_load_days is not None else int(cfg.initial_load_days)
        if days <= 0:
            raise TmsEliteConfigError("initial_load_days deve ser > 0")
        end = business_date
        start = business_date - timedelta(days=days)
        return self._run(
            job_id=job_id,
            business_date=business_date,
            filter_start=start,
            filter_end=end,
            dry_run=dry_run,
            actor=actor,
        )

    def run_daily(
        self,
        *,
        business_date: date,
        dry_run: bool = False,
        actor: str = "worker",
        job_id: str = "import_deliveries_daily",
        id_status: Optional[str] = None,
        id_servico: Optional[str] = None,
    ) -> DeliveryImportResult:
        return self._run(
            job_id=job_id,
            business_date=business_date,
            filter_start=business_date,
            filter_end=business_date,
            dry_run=dry_run,
            actor=actor,
            id_status=id_status,
            id_servico=id_servico,
        )

    def _require_config(self):
        cfg = self._api.get_default()
        if cfg is None:
            raise TmsEliteConfigError("Nenhuma configuração de API padrão ativa.")
        return cfg

    def _run(
        self,
        *,
        job_id: str,
        business_date: date,
        filter_start: date,
        filter_end: date,
        dry_run: bool,
        actor: str,
        id_status: Optional[str] = None,
        id_servico: Optional[str] = None,
    ) -> DeliveryImportResult:
        cfg = self._require_config()
        token = decrypt_secret(cfg.token_encrypted)
        client = TmsEliteClient(
            base_url=cfg.base_url,
            endpoint=cfg.endpoint,
            token=token,
            timeout_seconds=cfg.timeout_seconds,
            page_size=cfg.page_size,
        )
        integration = TmsEliteIntegrationService(client)

        log_id = None
        if not dry_run:
            log_id = self._logs.start(
                job_id=job_id,
                business_date=business_date,
                filter_start=filter_start,
                filter_end=filter_end,
                actor=actor,
            )

        try:
            fetched = integration.fetch_mapped(
                data_inicio=filter_start,
                data_fim=filter_end,
                id_status=id_status,
                id_servico=id_servico,
            )
            inserted = updated = 0
            if dry_run:
                message = (
                    f"Dry-run: {len(fetched.records)} registro(s) mapeados "
                    f"em {fetched.pages_processed} página(s)."
                )
                return DeliveryImportResult(
                    status="success",
                    message=message,
                    pages_processed=fetched.pages_processed,
                    rows_inserted=0,
                    rows_updated=0,
                    error_count=fetched.error_count,
                    filter_start=filter_start,
                    filter_end=filter_end,
                )

            if fetched.records:
                inserted, updated = self._deliveries.upsert_many(fetched.records, actor=actor)

            status = "partial" if fetched.error_count and (inserted or updated) else (
                "failed" if fetched.error_count and not fetched.records else "success"
            )
            message = (
                f"Importação {status}: +{inserted} / ~{updated} "
                f"páginas={fetched.pages_processed} erros_map={fetched.error_count}"
            )
            if log_id is not None:
                self._logs.finish(
                    log_id,
                    status=status if status != "partial" else "partial",
                    pages_processed=fetched.pages_processed,
                    rows_inserted=inserted,
                    rows_updated=updated,
                    error_count=fetched.error_count,
                    error_message="; ".join(fetched.errors) if fetched.errors else None,
                    actor=actor,
                )
            return DeliveryImportResult(
                status=status,
                message=message,
                pages_processed=fetched.pages_processed,
                rows_inserted=inserted,
                rows_updated=updated,
                error_count=fetched.error_count,
                filter_start=filter_start,
                filter_end=filter_end,
            )
        except TmsEliteError as exc:
            logger.exception("Falha na importação TMS Elite")
            if log_id is not None:
                self._logs.finish(
                    log_id,
                    status="failed",
                    error_count=1,
                    error_message=str(exc),
                    actor=actor,
                )
            return DeliveryImportResult(
                status="failed",
                message=str(exc),
                error_count=1,
                filter_start=filter_start,
                filter_end=filter_end,
            )
