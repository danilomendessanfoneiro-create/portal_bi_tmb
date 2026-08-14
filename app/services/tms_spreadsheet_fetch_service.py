"""Orquestra coleta TMS Elite → ManualImportService (mesmo fluxo do upload admin)."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Optional

from app.integrations.tmselite_rpa import TmsRpaError, download_geral_entregas
from app.services.job_schedule_service import AUTOMATION_TMS_SPREADSHEET, JobScheduleService
from app.services.manual_import_service import ManualImportError, ManualImportService

logger = logging.getLogger("tms_spreadsheet_fetch")

ACTOR = "auto"
IMPORT_POLL_SECONDS = 2
IMPORT_TIMEOUT_SECONDS = 1800
TERMINAL_OK = {"imported"}
TERMINAL_FAIL = {"failed", "validated_error"}


class TmsSpreadsheetFetchError(Exception):
    def __init__(self, message: str, *, step: str, extra: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.step = step
        self.extra = extra or {}


class TmsSpreadsheetFetchService:
    def __init__(
        self,
        *,
        schedules: Optional[JobScheduleService] = None,
        imports: Optional[ManualImportService] = None,
        downloader: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._schedules = schedules or JobScheduleService()
        self._imports = imports or ManualImportService()
        self._download = downloader or download_geral_entregas

    def run(self, *, dry_run: bool = False) -> dict[str, Any]:
        sched = self._schedules.get(AUTOMATION_TMS_SPREADSHEET)
        if sched is None:
            raise TmsSpreadsheetFetchError("Automação TMS não cadastrada.", step="config")
        password = self._schedules.get_tms_password()
        if not (sched.tms_login_url and sched.tms_username and password):
            raise TmsSpreadsheetFetchError(
                "Preencha URL, usuário e senha em Automações → Importação de pedidos.",
                step="config",
            )

        headless = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() != "false"
        logger.info(
            "Iniciando coleta TMS user=%s url=%s dry_run=%s",
            sched.tms_username,
            sched.tms_login_url,
            dry_run,
        )
        try:
            downloaded = self._download(
                login_url=sched.tms_login_url,
                username=sched.tms_username,
                password=password,
                headless=headless,
            )
        except TmsRpaError as exc:
            raise TmsSpreadsheetFetchError(exc.message, step=exc.step) from exc

        metrics: dict[str, Any] = {
            "file_name": downloaded.file_name,
            "file_size": downloaded.size_bytes,
            "sha256": downloaded.sha256,
            "tms_username": sched.tms_username,
        }
        if dry_run:
            metrics["dry_run"] = True
            logger.info("dry-run: arquivo baixado, importação ignorada")
            return metrics

        try:
            batch = self._imports.upload(
                filename=downloaded.file_name,
                content=downloaded.content,
                mtime=None,
                actor=ACTOR,
            )
            batch_id = int(batch["id"])
            metrics["batch_id"] = batch_id
            metrics["total_rows"] = int(batch.get("total_rows") or 0)
            logger.info("upload ok batch_id=%s rows=%s", batch_id, metrics["total_rows"])

            validated = self._imports.validate(batch_id, actor=ACTOR)
            status = str(validated.get("status") or "")
            metrics["valid_rows"] = int(validated.get("valid_rows") or 0)
            metrics["error_rows"] = int(validated.get("error_rows") or 0)
            metrics["validation_status"] = status
            if status != "validated_ok":
                raise TmsSpreadsheetFetchError(
                    validated.get("error_message") or "Planilha fora do padrão / validação com erros.",
                    step="validate",
                    extra=metrics,
                )

            self._imports.start_import(batch_id, actor=ACTOR, wait=True)
            imported = self._wait_import(batch_id)
            metrics["import_status"] = imported.get("status")
            metrics["rows_inserted"] = int(imported.get("rows_inserted") or 0)
            metrics["rows_updated"] = int(imported.get("rows_updated") or 0)
            return metrics
        except ManualImportError as exc:
            raise TmsSpreadsheetFetchError(str(exc), step="import", extra=metrics) from exc

    def _wait_import(self, batch_id: int) -> dict[str, Any]:
        deadline = time.time() + IMPORT_TIMEOUT_SECONDS
        while time.time() < deadline:
            batch = self._imports.get_batch(batch_id) or {}
            status = str(batch.get("status") or "")
            if status in TERMINAL_OK:
                return batch
            if status in TERMINAL_FAIL:
                raise TmsSpreadsheetFetchError(
                    batch.get("error_message") or f"Importação terminou com status {status}.",
                    step="import",
                    extra={"batch_id": batch_id, "import_status": status},
                )
            time.sleep(IMPORT_POLL_SECONDS)
        raise TmsSpreadsheetFetchError(
            "Timeout aguardando conclusão da importação.",
            step="import",
            extra={"batch_id": batch_id},
        )
