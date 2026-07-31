"""Capture immutable daily overdue snapshots for historical BI."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

import pandas as pd

from app.repositories.bi_snapshot_repository import BiSnapshotRepository

logger = logging.getLogger("bi_snapshot")

RULE_VERSION = "macros-v1"

OVERDUE_DAY_COLUMNS = [
    "business_date",
    "remessa_numero",
    "nro_entrega",
    "nota_fiscal",
    "filial",
    "cliente",
    "cidade_entrega",
    "uf_entrega",
    "status",
    "motorista",
    "dias_atraso",
    "valor_total",
    "prazo_considerado",
    "status_prazo",
]


@dataclass
class SnapshotCaptureResult:
    status: str  # created | skipped | failed
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


def _as_int(value: Any) -> Optional[int]:
    number = _as_float(value)
    if number is None:
        return None
    return int(number)


def _as_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.to_pydatetime().replace(tzinfo=None)


def dataframe_to_overdue_rows(overdue: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if overdue is None or overdue.empty:
        return rows
    for _, row in overdue.iterrows():
        remessa = _as_str(row.get("remessa_numero")) or _as_str(row.get("nro_entrega"))
        if not remessa:
            continue
        rows.append(
            {
                "remessa_numero": remessa,
                "nro_entrega": _as_str(row.get("nro_entrega")) or remessa,
                "nota_fiscal": _as_str(row.get("nota_fiscal")),
                "filial": _as_str(row.get("filial")),
                "cliente": _as_str(row.get("cliente")),
                "cidade_entrega": _as_str(row.get("cidade_entrega")),
                "uf_entrega": _as_str(row.get("uf_entrega")),
                "status": _as_str(row.get("status")),
                "motorista": _as_str(row.get("motorista")),
                "dias_atraso": _as_int(row.get("dias_atraso")) or 0,
                "valor_total": _as_float(row.get("valor_total")),
                "prazo_considerado": _as_dt(row.get("prazo_considerado")),
                "status_prazo": _as_str(row.get("status_prazo")),
            }
        )
    return rows


class BiSnapshotService:
    def __init__(self, repo: Optional[BiSnapshotRepository] = None) -> None:
        self._repo = repo or BiSnapshotRepository()

    def capture_if_absent(
        self,
        business_date: date,
        overdue: pd.DataFrame,
        *,
        actor: str = "worker",
        source: str = "job",
        source_job_id: Optional[str] = "report_overdue_daily",
        source_run_id: Optional[int] = None,
        captured_on: Optional[datetime] = None,
    ) -> SnapshotCaptureResult:
        existing = self._repo.get_run_by_business_date(business_date)
        if existing is not None:
            return SnapshotCaptureResult(
                status="skipped",
                message=f"Snapshot já existe para {business_date.isoformat()}",
                run_id=int(existing["id"]),
                rows=int(existing.get("total_overdue") or 0),
            )

        rows = dataframe_to_overdue_rows(overdue)
        total_value = None
        values = [r["valor_total"] for r in rows if r.get("valor_total") is not None]
        if values:
            total_value = float(sum(values))

        try:
            run_id = self._repo.insert_run(
                business_date=business_date,
                total_overdue=len(rows),
                total_value_overdue=total_value,
                source=source,
                rule_version=RULE_VERSION,
                source_job_id=source_job_id,
                source_run_id=source_run_id,
                actor=actor,
                captured_on=captured_on,
            )
            inserted = self._repo.insert_overdue_rows(
                snapshot_run_id=run_id,
                business_date=business_date,
                rows=rows,
                actor=actor,
            )
            return SnapshotCaptureResult(
                status="created",
                message=f"Snapshot {business_date.isoformat()}: {inserted} linha(s)",
                run_id=run_id,
                rows=inserted,
            )
        except Exception as exc:
            logger.exception("Falha ao gravar snapshot %s", business_date)
            return SnapshotCaptureResult(
                status="failed",
                message=str(exc),
            )

    def capture_replace(
        self,
        business_date: date,
        overdue: pd.DataFrame,
        *,
        actor: str = "worker",
        source: str = "manual_import",
        source_job_id: Optional[str] = "manual_import",
        source_run_id: Optional[int] = None,
        captured_on: Optional[datetime] = None,
    ) -> SnapshotCaptureResult:
        """Recria o snapshot do dia (usado após importação de planilha)."""
        replaced_id = self._repo.delete_run_by_business_date(business_date)
        result = self.capture_if_absent(
            business_date,
            overdue,
            actor=actor,
            source=source,
            source_job_id=source_job_id,
            source_run_id=source_run_id,
            captured_on=captured_on,
        )
        if result.status == "created" and replaced_id is not None:
            result = SnapshotCaptureResult(
                status="replaced",
                message=f"Snapshot {business_date.isoformat()} substituído: {result.rows} linha(s)",
                run_id=result.run_id,
                rows=result.rows,
            )
        return result

    def filter_options(
        self,
        *,
        date_from: date,
        date_to: date,
        filiais: Optional[list[str]] = None,
    ) -> dict[str, list[str]]:
        return self._repo.list_filter_values(
            date_from=date_from,
            date_to=date_to,
            filiais=filiais or None,
        )

    def aggregate_series(
        self,
        *,
        date_from: date,
        date_to: date,
        filiais: Optional[list[str]] = None,
        clientes: Optional[list[str]] = None,
        cidades: Optional[list[str]] = None,
        busca: Optional[str] = None,
    ) -> pd.DataFrame:
        rows = self._repo.aggregate_overdue_by_day(
            date_from=date_from,
            date_to=date_to,
            filiais=filiais or None,
            clientes=clientes or None,
            cidades=cidades or None,
            busca=busca,
        )
        if not rows:
            return pd.DataFrame(columns=["business_date", "overdue_count"])
        df = pd.DataFrame(rows)
        df["business_date"] = pd.to_datetime(df["business_date"]).dt.date
        return df

    def list_overdue_for_day(
        self,
        *,
        business_date: date,
        filiais: Optional[list[str]] = None,
        clientes: Optional[list[str]] = None,
        cidades: Optional[list[str]] = None,
        busca: Optional[str] = None,
    ) -> pd.DataFrame:
        """Linhas do snapshot de um dia (somente atrasados da foto). Não lê prb_deliveries."""
        rows = self._repo.list_overdue_for_day(
            business_date=business_date,
            filiais=filiais or None,
            clientes=clientes or None,
            cidades=cidades or None,
            busca=busca,
        )
        if not rows:
            return pd.DataFrame(columns=OVERDUE_DAY_COLUMNS)
        df = pd.DataFrame(rows)
        if "business_date" in df.columns:
            df["business_date"] = pd.to_datetime(df["business_date"]).dt.date
        if "prazo_considerado" in df.columns:
            df["prazo_considerado"] = pd.to_datetime(df["prazo_considerado"], errors="coerce")
        if "dias_atraso" in df.columns:
            df["dias_atraso"] = pd.to_numeric(df["dias_atraso"], errors="coerce").fillna(0).astype(int)
        if "valor_total" in df.columns:
            df["valor_total"] = pd.to_numeric(df["valor_total"], errors="coerce")
        return df
