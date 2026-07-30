"""Import deliveries from the spreadsheet CSV into prb_deliveries."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from app.config import settings
from app.integrations.tmselite.models import DeliveryRecord
from app.repositories.delivery_repository import DeliveryRepository
from limpeza import (
    carregar_dados_brutos,
    remover_duplicados_e_invalidos,
    selecionar_colunas,
    tratar_tipos,
)


@dataclass
class CsvImportResult:
    status: str
    message: str
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_deleted: int = 0
    rows_read: int = 0


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat", "-"}:
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


def _as_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    ts = pd.Timestamp(value)
    if pd.isna(ts):
        return None
    return ts.to_pydatetime().replace(tzinfo=None)


def map_csv_row(row: pd.Series) -> DeliveryRecord:
    nro = _as_str(row.get("nro_entrega"))
    if not nro:
        raise ValueError("Linha sem nro_entrega")
    return DeliveryRecord(
        remessa_numero=nro,
        nro_entrega=nro,
        nota_fiscal=_as_str(row.get("nota_fiscal")),
        cliente=_as_str(row.get("cliente")),
        filial=_as_str(row.get("filial")),
        cidade_entrega=_as_str(row.get("cidade_entrega")),
        uf_entrega=_as_str(row.get("uf_entrega")),
        status=_as_str(row.get("status")),
        valor_total=_as_float(row.get("valor_total")),
        qtde_volumes=_as_float(row.get("qtde_volumes")),
        dt_prazo_atual=_as_dt(row.get("dt_prazo_atual")),
        dt_agendamento=_as_dt(row.get("dt_agendamento")),
        dt_entrega=_as_dt(row.get("dt_entrega")),
        dt_cancelamento=_as_dt(row.get("dt_cancelamento")),
        motivo_cancelamento=_as_str(row.get("motivo_cancelamento")),
        motivo_atraso=_as_str(row.get("motivo_atraso")),
        nome_recebedor=_as_str(row.get("nome_recebedor")),
        dt_cadastro=_as_dt(row.get("dt_cadastro")),
        motorista=_as_str(row.get("motorista")),
        remetente=_as_str(row.get("remetente")),
        cidade_remetente=_as_str(row.get("cidade_remetente")),
        uf_remetente=_as_str(row.get("uf_remetente")),
        peso_taxado=_as_float(row.get("peso_taxado")),
        peso_informado=_as_float(row.get("peso_informado")),
        raw_json={"source": "csv", "nro_entrega": nro},
    )


class CsvDeliveryImportService:
    def __init__(self, deliveries: Optional[DeliveryRepository] = None) -> None:
        self._deliveries = deliveries or DeliveryRepository()

    def run(
        self,
        *,
        csv_path: Optional[Path] = None,
        replace: bool = True,
        dry_run: bool = False,
        actor: str = "csv-migrate",
    ) -> CsvImportResult:
        path = Path(csv_path) if csv_path else settings.data_csv
        if not path.is_file():
            return CsvImportResult(
                status="failed",
                message=f"CSV não encontrado: {path}",
            )

        df = carregar_dados_brutos(str(path))
        df = selecionar_colunas(df)
        df = tratar_tipos(df)
        df = remover_duplicados_e_invalidos(df)

        records: list[DeliveryRecord] = []
        for _, row in df.iterrows():
            try:
                records.append(map_csv_row(row))
            except ValueError:
                continue

        if dry_run:
            return CsvImportResult(
                status="success",
                message=f"Dry-run: {len(records)} registro(s) prontos a partir de {path.name}",
                rows_read=len(records),
            )

        deleted = 0
        if replace:
            deleted = self._deliveries.delete_all()

        inserted, updated = self._deliveries.upsert_many(
            records,
            actor=actor,
            source="csv",
        )
        return CsvImportResult(
            status="success",
            message=(
                f"CSV importado: +{inserted} / ~{updated}"
                + (f" (apagados {deleted})" if replace else "")
                + f" a partir de {path.name}"
            ),
            rows_inserted=inserted,
            rows_updated=updated,
            rows_deleted=deleted,
            rows_read=len(records),
        )
