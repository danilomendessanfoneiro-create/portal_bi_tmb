"""Capture Progressão snapshots from manual-import batches (pós calcConsolidada)."""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

import pandas as pd

from app.repositories.progress_snapshot_repository import ProgressSnapshotRepository
from app.services.macro_delivery_rules import aplicar_regras_macros

logger = logging.getLogger("progress_snapshot")

RULE_VERSION = "calc-consolidada-v1"
SOURCE_MANUAL_IMPORT = "manual_import"
STATUS_PRAZO_SEM = "(sem prazo)"

_DIGITS_RE = re.compile(r"\D+")


@dataclass
class ProgressCaptureResult:
    status: str  # created | skipped | failed | replaced
    message: str
    run_id: Optional[int] = None
    rows: int = 0


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat"}:
        return None
    return text


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _normalize_cnpj(value: Any) -> Optional[str]:
    text = _as_str(value)
    if not text:
        return None
    digits = _DIGITS_RE.sub("", text)
    return digits or None


def _reference_date(captured_at: Any) -> date:
    if captured_at is None:
        return datetime.now().date()
    if isinstance(captured_at, datetime):
        return captured_at.date()
    if isinstance(captured_at, date):
        return captured_at
    ts = pd.Timestamp(captured_at)
    if pd.isna(ts):
        return datetime.now().date()
    return ts.date()


def prepare_progress_frame(
    rows: list[dict[str, Any]] | pd.DataFrame,
    *,
    data_referencia: date | datetime | None = None,
) -> pd.DataFrame:
    """Aplica calcConsolidada (exclui ENTREGUE + STATUS PRAZO) antes de materializar o snapshot."""
    if isinstance(rows, pd.DataFrame):
        df = rows.copy() if not rows.empty else pd.DataFrame()
    else:
        df = pd.DataFrame(list(rows or []))
    if df.empty:
        return df
    return aplicar_regras_macros(df, data_referencia=data_referencia)


def rows_to_progress_items(rows: list[dict[str, Any]] | pd.DataFrame) -> list[dict[str, Any]]:
    """Normaliza linhas já processadas; dedupe por nro_entrega; status_prazo com fallback."""
    if isinstance(rows, pd.DataFrame):
        records = rows.to_dict(orient="records") if not rows.empty else []
    else:
        records = list(rows or [])

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in records:
        nro = _as_str(row.get("nro_entrega")) or _as_str(row.get("remessa_numero"))
        if not nro or nro in seen:
            continue
        status = (
            _as_str(row.get("status"))
            or _as_str(row.get("status_entrega"))
            or "DESCONHECIDO"
        )
        status_prazo = _as_str(row.get("status_prazo")) or STATUS_PRAZO_SEM
        cnpj = row.get("cnpj_cliente")
        if not cnpj:
            payload = row.get("payload")
            if isinstance(payload, dict):
                cnpj = (
                    payload.get("cnpj_cliente")
                    or payload.get("cnpj_cliente_raw")
                    or payload.get("CNPJ Cliente")
                )
        seen.add(nro)
        items.append(
            {
                "nro_entrega": nro,
                "remessa_numero": _as_str(row.get("remessa_numero")) or nro,
                "status": status,
                "status_prazo": status_prazo,
                "filial": _as_str(row.get("filial")),
                "cliente": _as_str(row.get("cliente")),
                "cliente_conta": _as_str(row.get("cliente_conta")),
                "cnpj_cliente": _normalize_cnpj(cnpj),
                "cidade_entrega": _as_str(row.get("cidade_entrega")),
                "uf_entrega": _as_str(row.get("uf_entrega")),
                "motorista": _as_str(row.get("motorista")),
                "valor_total": _as_float(row.get("valor_total")),
            }
        )
    return items


class ProgressSnapshotService:
    def __init__(self, repo: Optional[ProgressSnapshotRepository] = None) -> None:
        self._repo = repo or ProgressSnapshotRepository()

    def capture_for_batch(
        self,
        batch_id: int,
        rows: list[dict[str, Any]] | pd.DataFrame,
        *,
        actor: str = "manual_import",
        source: str = SOURCE_MANUAL_IMPORT,
        notes: Optional[str] = None,
        replace: bool = False,
        captured_at: Optional[Any] = None,
    ) -> ProgressCaptureResult:
        """
        Persiste snapshot pós-macros (sem ENTREGUE; dimensão principal = status_prazo).
        Sync API não deve chamar este método (decisão 2A).
        """
        existing = self._repo.get_run_by_batch_id(batch_id)
        if existing is not None and not replace:
            return ProgressCaptureResult(
                status="skipped",
                message=f"Snapshot de progressão já existe para batch {batch_id}",
                run_id=int(existing["id"]),
                rows=int(existing.get("row_count") or 0),
            )
        if existing is not None and replace:
            self._repo.delete_run_by_batch_id(batch_id)

        ref = _reference_date(captured_at)
        processed = prepare_progress_frame(rows, data_referencia=ref)
        items = rows_to_progress_items(processed)
        try:
            run_id = self._repo.insert_run(
                import_batch_id=batch_id,
                row_count=len(items),
                source=source,
                rule_version=RULE_VERSION,
                actor=actor,
                notes=notes,
                captured_at=captured_at,
            )
            inserted = self._repo.insert_items(
                snapshot_run_id=run_id,
                rows=items,
                actor=actor,
            )
            if inserted != len(items):
                self._repo.update_run_row_count(run_id, inserted, actor=actor)
            return ProgressCaptureResult(
                status="replaced" if replace and existing is not None else "created",
                message=f"Progressão batch {batch_id}: {inserted} linha(s)",
                run_id=run_id,
                rows=inserted,
            )
        except Exception as exc:
            logger.exception("Falha ao gravar snapshot de progressão batch %s", batch_id)
            return ProgressCaptureResult(status="failed", message=str(exc))

    def filter_options(
        self,
        *,
        date_from,
        date_to,
        filiais: Optional[list[str]] = None,
    ) -> dict[str, list[str]]:
        runs = self._repo.list_runs(date_from=date_from, date_to=date_to)
        run_ids = [int(r["id"]) for r in runs]
        return self._repo.list_filter_values(run_ids=run_ids, filiais=filiais or None)

    def status_series(
        self,
        *,
        date_from,
        date_to,
        filiais: Optional[list[str]] = None,
        clientes: Optional[list[str]] = None,
        cidades: Optional[list[str]] = None,
        statuses: Optional[list[str]] = None,
        busca: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], pd.DataFrame]:
        runs = self._repo.list_runs(date_from=date_from, date_to=date_to)
        empty_cols = ["snapshot_run_id", "status_prazo", "qty", "label"]
        if not runs:
            return [], pd.DataFrame(columns=empty_cols)
        run_ids = [int(r["id"]) for r in runs]
        rows = self._repo.count_by_status_per_run(
            run_ids=run_ids,
            filiais=filiais or None,
            clientes=clientes or None,
            cidades=cidades or None,
            statuses=statuses or None,
            busca=busca,
        )
        labels = {
            int(r["id"]): pd.Timestamp(r["captured_at"]).strftime("%d/%m %H:%M")
            for r in runs
        }
        df = (
            pd.DataFrame(rows)
            if rows
            else pd.DataFrame(columns=["snapshot_run_id", "status_prazo", "qty"])
        )
        if not df.empty:
            df["label"] = df["snapshot_run_id"].map(labels)
            # Compat: coluna "status" no pivot do controller aponta para status_prazo
            if "status_prazo" in df.columns and "status" not in df.columns:
                df["status"] = df["status_prazo"]
        return runs, df

    def count_pedidos_entregues(
        self,
        *,
        date_from,
        date_to,
        filiais: Optional[list[str]] = None,
        clientes: Optional[list[str]] = None,
        cidades: Optional[list[str]] = None,
        statuses: Optional[list[str]] = None,
        busca: Optional[str] = None,
    ) -> int:
        runs = self._repo.list_runs(date_from=date_from, date_to=date_to)
        if len(runs) < 2:
            return 0
        total = 0
        for i in range(1, len(runs)):
            total += self._repo.count_delivered_between_runs(
                prev_run_id=int(runs[i - 1]["id"]),
                curr_run_id=int(runs[i]["id"]),
                filiais=filiais or None,
                clientes=clientes or None,
                cidades=cidades or None,
                statuses=statuses or None,
                busca=busca,
            )
        return total

    def count_pedidos_consolidados(
        self,
        *,
        date_from,
        date_to,
        filiais: Optional[list[str]] = None,
        clientes: Optional[list[str]] = None,
        cidades: Optional[list[str]] = None,
        statuses: Optional[list[str]] = None,
        busca: Optional[str] = None,
    ) -> int:
        """Pedidos únicos no período (união de nro_entrega entre uploads)."""
        runs = self._repo.list_runs(date_from=date_from, date_to=date_to)
        if not runs:
            return 0
        return self._repo.count_distinct_nro_entrega(
            run_ids=[int(r["id"]) for r in runs],
            filiais=filiais or None,
            clientes=clientes or None,
            cidades=cidades or None,
            statuses=statuses or None,
            busca=busca,
        )
