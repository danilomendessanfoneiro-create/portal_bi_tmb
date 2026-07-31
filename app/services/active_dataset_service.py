"""Resolve the active analysis dataset (last spreadsheet import or last API sync)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.repositories.base import get_connection


API_IMPORT_JOB_IDS = (
    "import_deliveries",
    "import_deliveries_daily",
    "import_deliveries_initial",
)


@dataclass(frozen=True)
class ActiveDataset:
    source: str  # manual_import | api_sync
    batch_id: Optional[int] = None
    sync_id: Optional[int] = None
    label: str = ""
    activated_on: Optional[datetime] = None
    row_count: Optional[int] = None
    empty_reason: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        return self.source == "empty"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "batch_id": self.batch_id,
            "sync_id": self.sync_id,
            "label": self.label,
            "activated_on": self.activated_on.isoformat(sep=" ", timespec="seconds")
            if isinstance(self.activated_on, datetime)
            else self.activated_on,
            "row_count": self.row_count,
            "empty_reason": self.empty_reason,
        }


EMPTY_DATASET = ActiveDataset(
    source="empty",
    label="",
    empty_reason="Nenhum lote ativo. Importe uma planilha ou execute a sincronização da API.",
)


class ActiveDatasetService:
    """
    Regra FR-3: preferir último batch manual `imported`;
    senão última sync API success; senão vazio.
    Planilha permanece ativa mesmo se a API rodar depois (até novo upload).
    """

    def resolve(self) -> ActiveDataset:
        batch = self._latest_imported_batch()
        if batch:
            batch_id = int(batch["id"])
            count = self._count_deliveries(dataset_batch_id=batch_id)
            return ActiveDataset(
                source="manual_import",
                batch_id=batch_id,
                label=str(batch.get("file_name") or f"Lote #{batch_id}"),
                activated_on=batch.get("finished_on") or batch.get("modified_on"),
                row_count=count,
            )

        run = self._latest_api_sync_success()
        if run:
            sync_id = int(run["id"])
            count = self._count_deliveries(dataset_sync_id=sync_id)
            label = f"Sync API #{sync_id} ({run.get('job_id')})"
            return ActiveDataset(
                source="api_sync",
                sync_id=sync_id,
                label=label,
                activated_on=run.get("finished_on") or run.get("started_on"),
                row_count=count,
            )

        return EMPTY_DATASET

    def remember(
        self,
        *,
        source: str,
        actor: str,
        batch_id: Optional[int] = None,
        sync_id: Optional[int] = None,
        label: str = "",
        row_count: Optional[int] = None,
    ) -> None:
        """Cache opcional do ponteiro (UI); resolve() não depende só disso."""
        if source == "api_sync" and self._latest_imported_batch():
            # Planilha tem prioridade: não sobrescrever cache com API
            return
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO prb_active_dataset (
                    id, source, batch_id, sync_id, label, activated_on, row_count,
                    created_by, created_on, modified_by, modified_on, enabled
                ) VALUES (
                    1, %s, %s, %s, %s, NOW(), %s,
                    %s, NOW(), %s, NOW(), TRUE
                )
                ON CONFLICT (id) DO UPDATE SET
                    source = EXCLUDED.source,
                    batch_id = EXCLUDED.batch_id,
                    sync_id = EXCLUDED.sync_id,
                    label = EXCLUDED.label,
                    activated_on = NOW(),
                    row_count = EXCLUDED.row_count,
                    modified_by = EXCLUDED.modified_by,
                    modified_on = NOW(),
                    enabled = TRUE
                """,
                [source, batch_id, sync_id, label, row_count, actor, actor],
            )

    def _latest_imported_batch(self) -> Optional[dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, file_name, finished_on, modified_on, created_on
                FROM prb_import_batches
                WHERE enabled = TRUE AND status = 'imported'
                ORDER BY COALESCE(finished_on, modified_on, created_on) DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
        return dict(row) if row else None

    def _latest_api_sync_success(self) -> Optional[dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, job_id, started_on, finished_on, business_date
                FROM prb_job_runs
                WHERE status = 'success'
                  AND job_id = ANY(%s)
                ORDER BY COALESCE(finished_on, started_on) DESC, id DESC
                LIMIT 1
                """,
                [list(API_IMPORT_JOB_IDS)],
            ).fetchone()
        return dict(row) if row else None

    def _count_deliveries(
        self,
        *,
        dataset_batch_id: Optional[int] = None,
        dataset_sync_id: Optional[int] = None,
    ) -> int:
        with get_connection() as conn:
            if dataset_batch_id is not None:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS total FROM prb_deliveries
                    WHERE enabled = TRUE AND dataset_batch_id = %s
                    """,
                    [dataset_batch_id],
                ).fetchone()
            elif dataset_sync_id is not None:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS total FROM prb_deliveries
                    WHERE enabled = TRUE AND dataset_sync_id = %s
                    """,
                    [dataset_sync_id],
                ).fetchone()
            else:
                return 0
        return int(row["total"]) if row else 0
