"""Manual spreadsheet import: upload → staging → validate → upsert."""

from __future__ import annotations

import math
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from app.config import settings
from app.integrations.tmselite.models import DeliveryRecord
from app.repositories.base import get_connection
from app.repositories.delivery_repository import DeliveryRepository
from app.repositories.import_repository import ImportRepository
from app.services.branch_catalog_service import BranchCatalogService
from app.services.csv_delivery_import_service import map_csv_row
from limpeza import COLUNAS_UTEIS, carregar_dados_brutos, selecionar_colunas, tratar_tipos

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_ROWS = 100_000
ALLOWED_EXT = {".csv", ".xlsx", ".xls"}
REQUIRED_INTERNAL = ["nro_entrega", "filial"]


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _as_python_dt(value: Any) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime()
        except Exception:
            pass
    return value


def _json_safe(value: Any) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


class ManualImportError(Exception):
    pass


@dataclass
class UploadMeta:
    name: str
    size: int
    mtime: Optional[datetime]


class ManualImportService:
    def __init__(
        self,
        imports: Optional[ImportRepository] = None,
        deliveries: Optional[DeliveryRepository] = None,
        branches: Optional[BranchCatalogService] = None,
    ) -> None:
        self._imports = imports or ImportRepository()
        self._deliveries = deliveries or DeliveryRepository()
        self._branches = branches or BranchCatalogService()

    @property
    def storage_dir(self) -> Path:
        path = settings.root_dir / "storage" / "imports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def upload(
        self,
        *,
        filename: str,
        content: bytes,
        mtime: Optional[datetime],
        actor: str,
    ) -> dict[str, Any]:
        if not content:
            raise ManualImportError("Arquivo vazio.")
        if len(content) > MAX_FILE_BYTES:
            raise ManualImportError("Arquivo excede o limite de 20 MB.")

        name = Path(filename).name
        ext = Path(name).suffix.lower()
        if ext not in ALLOWED_EXT:
            raise ManualImportError("Formato inválido. Use .csv, .xlsx ou .xls.")

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        stored = self.storage_dir / f"{stamp}_{actor}_{safe}"
        stored.write_bytes(content)

        try:
            df_raw = self._load_dataframe(stored, ext)
        except Exception as exc:
            stored.unlink(missing_ok=True)
            raise ManualImportError(f"Arquivo corrompido ou ilegível: {exc}") from exc

        if df_raw.empty:
            stored.unlink(missing_ok=True)
            raise ManualImportError("Planilha sem dados.")
        if len(df_raw) > MAX_ROWS:
            stored.unlink(missing_ok=True)
            raise ManualImportError(f"Planilha excede o limite de {MAX_ROWS:,} linhas.".replace(",", "."))

        batch = self._imports.create_batch(
            file_name=name,
            file_ext=ext.lstrip("."),
            file_size_bytes=len(content),
            file_path=str(stored),
            file_mtime=mtime,
            actor=actor,
        )
        try:
            items = self._dataframe_to_staging_items(df_raw)
            self._imports.replace_items(int(batch["id"]), items, actor=actor)
            return self._imports.update_batch(
                int(batch["id"]),
                {"total_rows": len(items), "status": "uploaded"},
                actor=actor,
            )
        except Exception:
            stored.unlink(missing_ok=True)
            raise

    def validate(self, batch_id: int, *, actor: str) -> dict[str, Any]:
        batch = self._imports.get_batch(batch_id)
        if not batch:
            raise ManualImportError("Lote não encontrado.")

        self._imports.update_batch(batch_id, {"status": "validating"}, actor=actor)
        items = self._imports.list_items(batch_id)
        known_branches = self._branches.list_enabled_filial_branches()
        errors: list[dict[str, Any]] = []
        seen_keys: dict[str, int] = {}

        # Structure: required columns present in staging payloads / mapped fields
        if not items:
            errors.append({"row_number": None, "message": "Nenhum registro na planilha."})

        for item in items:
            row_no = int(item["row_number"])
            row_errors: list[str] = []

            nro = (item.get("nro_entrega") or item.get("remessa_numero") or "").strip()
            if not nro:
                row_errors.append("Número da entrega não informado.")
            else:
                if nro in seen_keys:
                    row_errors.append(
                        f"Entrega {nro} duplicada na planilha (também na linha {seen_keys[nro]})."
                    )
                else:
                    seen_keys[nro] = row_no

            filial = (item.get("filial") or "").strip()
            if not filial:
                row_errors.append("Filial não informada.")
            elif not self._branches.is_known_branch(filial, known_branches):
                row_errors.append(
                    f"Código da Filial inexistente ({filial}). {BranchCatalogService.SUGGEST_MESSAGE}"
                )

            cliente = item.get("cliente")
            if cliente is None or str(cliente).strip() == "":
                row_errors.append("Cliente não informado.")

            # Invalid numeric already coerced to None in tratar_tipos — flag empty valor if present as bad string in payload
            payload = item.get("payload") or {}
            if isinstance(payload, str):
                payload = {}
            raw_valor = payload.get("valor_total_raw")
            if raw_valor not in (None, "", "-") and item.get("valor_total") is None:
                row_errors.append("Valor da entrega inválido.")

            for dt_field, label in (
                ("dt_prazo_atual", "data de prazo"),
                ("dt_agendamento", "data de agendamento"),
                ("dt_entrega", "data de entrega"),
                ("dt_recebimento", "data de recebimento"),
                ("dt_cadastro", "data de cadastro"),
            ):
                raw = payload.get(f"{dt_field}_raw")
                if raw not in (None, "", "-") and item.get(dt_field) is None:
                    row_errors.append(f"Pedido/entrega possui {label} no formato inválido.")

            if row_errors:
                msg = f"Linha {row_no}: " + " ".join(row_errors)
                errors.append({"row_number": row_no, "message": msg})
                item["is_valid"] = False
                item["error_message"] = msg
            else:
                item["is_valid"] = True
                item["error_message"] = None

        # Persist item validity
        self._imports.replace_items(batch_id, items, actor=actor)
        logs = [{"row_number": e["row_number"], "level": "error", "message": e["message"]} for e in errors]
        self._imports.replace_logs(batch_id, logs, actor=actor)

        valid_rows = sum(1 for i in items if i.get("is_valid"))
        error_rows = len(items) - valid_rows
        status = "validated_ok" if not errors else "validated_error"
        updated = self._imports.update_batch(
            batch_id,
            {
                "status": status,
                "total_rows": len(items),
                "valid_rows": valid_rows,
                "error_rows": error_rows,
                "validation_errors": errors[:500],
                "error_message": None if not errors else f"{len(errors)} inconsistência(s) encontrada(s).",
            },
            actor=actor,
        )
        if status == "validated_error":
            self._purge_stored_file(batch_id, actor=actor)
            updated = self._imports.get_batch(batch_id) or updated
        return updated

    def start_import(self, batch_id: int, *, actor: str) -> dict[str, Any]:
        batch = self._imports.get_batch(batch_id)
        if not batch:
            raise ManualImportError("Lote não encontrado.")
        if batch["status"] != "validated_ok":
            raise ManualImportError("Importação só é permitida após validação sem erros.")
        file_path = str(batch.get("file_path") or "").strip()
        if file_path and not Path(file_path).is_file():
            raise ManualImportError(
                "Arquivo da planilha não está mais disponível. Faça um novo upload para importar."
            )

        self._imports.update_batch(
            batch_id,
            {
                "status": "importing",
                "started_on": datetime.now(),
                "progress_pct": 0,
                "rows_processed": 0,
                "rows_inserted": 0,
                "rows_updated": 0,
                "error_message": None,
            },
            actor=actor,
        )

        thread = threading.Thread(
            target=self._run_import_job,
            kwargs={"batch_id": batch_id, "actor": actor},
            daemon=True,
        )
        thread.start()
        return self._imports.get_batch(batch_id) or batch

    def soft_delete(self, batch_id: int, *, actor: str) -> dict[str, Any]:
        batch = self._imports.get_batch(batch_id)
        if not batch:
            raise ManualImportError("Lote não encontrado.")
        if batch["status"] not in {"validated_error", "failed"}:
            raise ManualImportError("Exclusão lógica só é permitida para lotes com erro.")
        self._purge_stored_file(batch_id, actor=actor)
        deleted = self._imports.soft_delete(batch_id, actor=actor)
        if not deleted:
            raise ManualImportError("Lote não encontrado.")
        return deleted

    def _purge_stored_file(self, batch_id: int, *, actor: str) -> None:
        batch = self._imports.get_batch(batch_id)
        if not batch:
            return
        path_str = str(batch.get("file_path") or "").strip()
        if path_str:
            try:
                Path(path_str).unlink(missing_ok=True)
            except OSError:
                pass
        if path_str:
            self._imports.update_batch(batch_id, {"file_path": ""}, actor=actor)

    def _run_import_job(self, *, batch_id: int, actor: str) -> None:
        started = datetime.now()
        try:
            items = self._imports.list_items(batch_id)
            records: list[DeliveryRecord] = []
            for item in items:
                row = pd.Series(
                    {
                        "nro_entrega": item.get("nro_entrega") or item.get("remessa_numero"),
                        "nota_fiscal": item.get("nota_fiscal"),
                        "cliente": item.get("cliente"),
                        "cliente_conta": item.get("cliente_conta"),
                        "filial": item.get("filial"),
                        "cidade_entrega": item.get("cidade_entrega"),
                        "uf_entrega": item.get("uf_entrega"),
                        "status": item.get("status_entrega"),
                        "valor_total": item.get("valor_total"),
                        "qtde_volumes": item.get("qtde_volumes"),
                        "dt_prazo_atual": item.get("dt_prazo_atual"),
                        "dt_agendamento": item.get("dt_agendamento"),
                        "dt_entrega": item.get("dt_entrega"),
                        "dt_recebimento": item.get("dt_recebimento"),
                        "dt_cancelamento": item.get("dt_cancelamento"),
                        "motivo_cancelamento": item.get("motivo_cancelamento"),
                        "motivo_atraso": item.get("motivo_atraso"),
                        "nome_recebedor": item.get("nome_recebedor"),
                        "dt_cadastro": item.get("dt_cadastro"),
                        "motorista": item.get("motorista"),
                        "remetente": item.get("remetente"),
                        "cidade_remetente": item.get("cidade_remetente"),
                        "uf_remetente": item.get("uf_remetente"),
                        "peso_taxado": item.get("peso_taxado"),
                        "peso_informado": item.get("peso_informado"),
                    }
                )
                records.append(map_csv_row(row))

            total = len(records)
            inserted = updated = 0
            with get_connection() as conn:
                chunk = max(1, min(200, total or 1))
                for i in range(0, total, chunk):
                    part = records[i : i + chunk]
                    ins, upd = self._deliveries.upsert_many(
                        part,
                        actor=actor,
                        source="manual_upload",
                        conn=conn,
                        dataset_batch_id=batch_id,
                        dataset_source="manual_import",
                    )
                    inserted += ins
                    updated += upd
                    processed = min(total, i + len(part))
                    pct = round(100.0 * processed / max(total, 1), 2)
                    # progresso visível em outra conexão (não compromete o rollback do lote)
                    self._imports.update_batch(
                        batch_id,
                        {
                            "rows_processed": processed,
                            "rows_inserted": inserted,
                            "rows_updated": updated,
                            "progress_pct": pct,
                        },
                        actor=actor,
                    )
            finished = datetime.now()
            duration_ms = int((finished - started).total_seconds() * 1000)
            self._imports.update_batch(
                batch_id,
                {
                    "status": "imported",
                    "finished_on": finished,
                    "duration_ms": duration_ms,
                    "progress_pct": 100,
                    "rows_processed": total,
                    "rows_inserted": inserted,
                    "rows_updated": updated,
                },
                actor=actor,
            )
            self._purge_stored_file(batch_id, actor=actor)
            try:
                from app.services.active_dataset_service import ActiveDatasetService

                batch_meta = self._imports.get_batch(batch_id) or {}
                ActiveDatasetService().remember(
                    source="manual_import",
                    actor=actor,
                    batch_id=batch_id,
                    label=str(batch_meta.get("file_name") or f"Lote #{batch_id}"),
                    row_count=total,
                )
            except Exception:
                pass
            self._capture_bi_snapshot_after_import(actor=actor)
        except Exception as exc:
            finished = datetime.now()
            duration_ms = int((finished - started).total_seconds() * 1000)
            self._imports.update_batch(
                batch_id,
                {
                    "status": "failed",
                    "finished_on": finished,
                    "duration_ms": duration_ms,
                    "error_message": str(exc),
                },
                actor=actor,
            )
            self._purge_stored_file(batch_id, actor=actor)

    def dispatch_report_emails(self, *, actor: str) -> dict[str, Any]:
        """Disparo manual do job de e-mails (não amarrado a um lote)."""
        try:
            cmd = [
                sys.executable,
                "-m",
                "worker",
                "run",
                "report_overdue_daily",
                "--force",
            ]
            proc = subprocess.Popen(
                cmd,
                cwd=str(settings.root_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {
                "status": "started",
                "message": "Envio de e-mails disparado. Os relatórios serão enviados em segundo plano.",
                "pid": proc.pid,
                "actor": actor,
            }
        except Exception as exc:
            raise ManualImportError(f"Falha ao disparar envio de e-mails: {exc}") from exc

    def _capture_bi_snapshot_after_import(self, *, actor: str) -> None:
        """Recalcula o snapshot do Histórico do dia com o lote ativo; falha não desfaz a importação."""
        try:
            from limpeza import processar_entregas
            from app.services.bi_snapshot_service import BiSnapshotService
            from zoneinfo import ZoneInfo

            business_date = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
            df = processar_entregas(data_referencia=business_date)
            overdue = df[df["atrasado"] == True].copy() if "atrasado" in df.columns else df.iloc[0:0]
            snap = BiSnapshotService().capture_replace(
                business_date,
                overdue,
                actor=actor,
                source="manual_import",
                source_job_id="manual_import",
            )
            if snap.status == "failed":
                return
        except Exception:
            return

    def get_batch(self, batch_id: int) -> dict[str, Any]:
        batch = self._imports.get_batch(batch_id)
        if not batch:
            raise ManualImportError("Lote não encontrado.")
        return batch

    def list_history(self, **kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        return self._imports.list_batches(**kwargs)

    def list_errors(self, batch_id: int) -> list[dict[str, Any]]:
        return self._imports.list_logs(batch_id)

    def _load_dataframe(self, path: Path, ext: str) -> pd.DataFrame:
        if ext == ".csv":
            return carregar_dados_brutos(str(path))
        # Excel: first sheet
        df = pd.read_excel(path, dtype=str, engine="openpyxl" if ext == ".xlsx" else None)
        if df is None or df.empty:
            raise ManualImportError("Aba da planilha inexistente ou vazia.")
        return df

    def _normalize_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(c).strip() if c is not None else "" for c in df.columns]
        return df

    def assert_spreadsheet_structure(self, df_raw: pd.DataFrame) -> list[str]:
        """Return blocking structure issues. Extra columns beyond COLUNAS_UTEIS are allowed (ignored)."""
        issues: list[str] = []
        cols = [str(c).strip() if c is not None else "" for c in df_raw.columns]
        seen: dict[str, int] = {}
        dups: list[str] = []
        for name in cols:
            if not name:
                continue
            seen[name] = seen.get(name, 0) + 1
            if seen[name] == 2:
                dups.append(name)
        if dups:
            issues.append(f"Colunas duplicadas na planilha: {', '.join(dups)}.")

        required = ["Nro. Entrega", "Sigla Unidade Entrega", "Nome Pessoa Visita"]
        missing = [c for c in required if c not in seen]
        if missing:
            issues.append(f"Colunas obrigatórias ausentes: {', '.join(missing)}.")
        return issues

    def _dataframe_to_staging_items(self, df_raw: pd.DataFrame) -> list[dict[str, Any]]:
        df_raw = self._normalize_headers(df_raw)
        raw_snapshot = df_raw.copy()
        structure = self.assert_spreadsheet_structure(df_raw)
        if structure:
            raise ManualImportError(" ".join(structure))

        df = selecionar_colunas(df_raw)
        df = tratar_tipos(df)
        items: list[dict[str, Any]] = []
        for idx, row in df.iterrows():
            row_number = len(items) + 2
            if isinstance(idx, (int, float)) and not (isinstance(idx, float) and math.isnan(idx)):
                row_number = int(idx) + 2

            payload: dict[str, Any] = {}
            for col in df.columns:
                payload[col] = _json_safe(row.get(col))
            if idx in raw_snapshot.index:
                raw_row = raw_snapshot.loc[idx]
                for src, dest in COLUNAS_UTEIS.items():
                    if src in raw_snapshot.columns:
                        val = raw_row.get(src)
                        payload[f"{dest}_raw"] = None if _is_missing(val) else str(val)

            nro = None if _is_missing(row.get("nro_entrega")) else str(row.get("nro_entrega")).strip()
            items.append(
                {
                    "row_number": row_number,
                    "remessa_numero": nro,
                    "nro_entrega": nro,
                    "nota_fiscal": None if _is_missing(row.get("nota_fiscal")) else str(row.get("nota_fiscal")),
                    "cliente": None if _is_missing(row.get("cliente")) else str(row.get("cliente")),
                    "cliente_conta": None
                    if _is_missing(row.get("cliente_conta"))
                    else str(row.get("cliente_conta")),
                    "filial": None if _is_missing(row.get("filial")) else str(row.get("filial")),
                    "cidade_entrega": None
                    if _is_missing(row.get("cidade_entrega"))
                    else str(row.get("cidade_entrega")),
                    "uf_entrega": None if _is_missing(row.get("uf_entrega")) else str(row.get("uf_entrega")),
                    "status_entrega": None if _is_missing(row.get("status")) else str(row.get("status")),
                    "valor_total": None if _is_missing(row.get("valor_total")) else float(row.get("valor_total")),
                    "qtde_volumes": None if _is_missing(row.get("qtde_volumes")) else float(row.get("qtde_volumes")),
                    "dt_prazo_atual": _as_python_dt(row.get("dt_prazo_atual")),
                    "dt_agendamento": _as_python_dt(row.get("dt_agendamento")),
                    "dt_entrega": _as_python_dt(row.get("dt_entrega")),
                    "dt_recebimento": _as_python_dt(row.get("dt_recebimento")),
                    "dt_cancelamento": _as_python_dt(row.get("dt_cancelamento")),
                    "motivo_cancelamento": None
                    if _is_missing(row.get("motivo_cancelamento"))
                    else str(row.get("motivo_cancelamento")),
                    "motivo_atraso": None if _is_missing(row.get("motivo_atraso")) else str(row.get("motivo_atraso")),
                    "nome_recebedor": None
                    if _is_missing(row.get("nome_recebedor"))
                    else str(row.get("nome_recebedor")),
                    "dt_cadastro": _as_python_dt(row.get("dt_cadastro")),
                    "motorista": None if _is_missing(row.get("motorista")) else str(row.get("motorista")),
                    "remetente": None if _is_missing(row.get("remetente")) else str(row.get("remetente")),
                    "cidade_remetente": None
                    if _is_missing(row.get("cidade_remetente"))
                    else str(row.get("cidade_remetente")),
                    "uf_remetente": None if _is_missing(row.get("uf_remetente")) else str(row.get("uf_remetente")),
                    "peso_taxado": None if _is_missing(row.get("peso_taxado")) else float(row.get("peso_taxado")),
                    "peso_informado": None
                    if _is_missing(row.get("peso_informado"))
                    else float(row.get("peso_informado")),
                    "payload": payload,
                    "is_valid": None,
                    "error_message": None,
                }
            )
        return items
