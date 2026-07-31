"""Persistence for manual spreadsheet import batches."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from app.repositories.base import get_connection


class ImportRepository:
    def create_batch(
        self,
        *,
        file_name: str,
        file_ext: str,
        file_size_bytes: int,
        file_path: str,
        file_mtime: Optional[datetime],
        actor: str,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO prb_import_batches (
                file_name, file_ext, file_size_bytes, file_path, file_mtime, status,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, %s, %s, %s, 'uploaded',
                %s, NOW(), %s, NOW(), TRUE
            )
            RETURNING *
        """
        with get_connection() as conn:
            row = conn.execute(
                sql,
                [file_name, file_ext, file_size_bytes, file_path, file_mtime, actor, actor],
            ).fetchone()
        return dict(row)

    def get_batch(self, batch_id: int) -> Optional[dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM prb_import_batches WHERE id = %s AND enabled = TRUE",
                [batch_id],
            ).fetchone()
        return dict(row) if row else None

    def update_batch(self, batch_id: int, fields: dict[str, Any], *, actor: str) -> dict[str, Any]:
        allowed = {
            "status",
            "total_rows",
            "valid_rows",
            "error_rows",
            "rows_processed",
            "rows_inserted",
            "rows_updated",
            "progress_pct",
            "validation_errors",
            "started_on",
            "finished_on",
            "duration_ms",
            "error_message",
            "report_job_status",
            "report_job_message",
            "file_path",
        }
        sets = []
        params: list[Any] = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            if key == "validation_errors":
                sets.append("validation_errors = %s::jsonb")
                params.append(json.dumps(value))
            else:
                sets.append(f"{key} = %s")
                params.append(value)
        sets.append("modified_by = %s")
        params.append(actor)
        sets.append("modified_on = NOW()")
        params.append(batch_id)
        sql = f"UPDATE prb_import_batches SET {', '.join(sets)} WHERE id = %s RETURNING *"
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row)

    def replace_items(self, batch_id: int, items: list[dict[str, Any]], *, actor: str) -> int:
        with get_connection() as conn:
            conn.execute("DELETE FROM prb_import_batch_items WHERE batch_id = %s", [batch_id])
            conn.execute("DELETE FROM prb_import_logs WHERE batch_id = %s", [batch_id])
            sql = """
                INSERT INTO prb_import_batch_items (
                    batch_id, row_number, remessa_numero, nro_entrega, nota_fiscal, cliente, cliente_conta,
                    filial, cidade_entrega, uf_entrega, status_entrega, valor_total, qtde_volumes,
                    dt_prazo_atual, dt_agendamento, dt_entrega, dt_recebimento, dt_cancelamento,
                    motivo_cancelamento, motivo_atraso, nome_recebedor, dt_cadastro, motorista,
                    remetente, cidade_remetente, uf_remetente, peso_taxado, peso_informado,
                    payload, is_valid, error_message,
                    created_by, created_on, modified_by, modified_on, enabled
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s::jsonb, %s, %s,
                    %s, NOW(), %s, NOW(), TRUE
                )
            """
            for item in items:
                conn.execute(
                    sql,
                    [
                        batch_id,
                        item["row_number"],
                        item.get("remessa_numero"),
                        item.get("nro_entrega"),
                        item.get("nota_fiscal"),
                        item.get("cliente"),
                        item.get("cliente_conta"),
                        item.get("filial"),
                        item.get("cidade_entrega"),
                        item.get("uf_entrega"),
                        item.get("status_entrega"),
                        item.get("valor_total"),
                        item.get("qtde_volumes"),
                        item.get("dt_prazo_atual"),
                        item.get("dt_agendamento"),
                        item.get("dt_entrega"),
                        item.get("dt_recebimento"),
                        item.get("dt_cancelamento"),
                        item.get("motivo_cancelamento"),
                        item.get("motivo_atraso"),
                        item.get("nome_recebedor"),
                        item.get("dt_cadastro"),
                        item.get("motorista"),
                        item.get("remetente"),
                        item.get("cidade_remetente"),
                        item.get("uf_remetente"),
                        item.get("peso_taxado"),
                        item.get("peso_informado"),
                        json.dumps(item.get("payload") or {}, default=str),
                        item.get("is_valid"),
                        item.get("error_message"),
                        actor,
                        actor,
                    ],
                )
        return len(items)

    def list_items(self, batch_id: int) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM prb_import_batch_items
                WHERE batch_id = %s AND enabled = TRUE
                ORDER BY row_number
                """,
                [batch_id],
            ).fetchall()
        return [dict(r) for r in rows]

    def replace_logs(self, batch_id: int, logs: list[dict[str, Any]], *, actor: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM prb_import_logs WHERE batch_id = %s", [batch_id])
            sql = """
                INSERT INTO prb_import_logs (
                    batch_id, row_number, level, message,
                    created_by, created_on, modified_by, modified_on, enabled
                ) VALUES (%s, %s, %s, %s, %s, NOW(), %s, NOW(), TRUE)
            """
            for log in logs:
                conn.execute(
                    sql,
                    [
                        batch_id,
                        log.get("row_number"),
                        log.get("level", "error"),
                        log["message"],
                        actor,
                        actor,
                    ],
                )

    def list_logs(self, batch_id: int) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM prb_import_logs
                WHERE batch_id = %s AND enabled = TRUE
                ORDER BY id
                """,
                [batch_id],
            ).fetchall()
        return [dict(r) for r in rows]

    def list_batches(
        self,
        *,
        search: Optional[str] = None,
        status: Optional[str] = None,
        created_by: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        where = ["enabled = TRUE"]
        params: list[Any] = []
        if search:
            where.append("file_name ILIKE %s")
            params.append(f"%{search.strip()}%")
        if status:
            where.append("status = %s")
            params.append(status)
        if created_by:
            where.append("created_by ILIKE %s")
            params.append(f"%{created_by.strip()}%")
        if date_from:
            where.append("created_on >= %s")
            params.append(date_from)
        if date_to:
            where.append("created_on <= %s")
            params.append(date_to)
        where_sql = " AND ".join(where)
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size
        with get_connection() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS total FROM prb_import_batches WHERE {where_sql}",
                params,
            ).fetchone()["total"]
            rows = conn.execute(
                f"""
                SELECT * FROM prb_import_batches
                WHERE {where_sql}
                ORDER BY created_on DESC
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            ).fetchall()
        return [dict(r) for r in rows], int(total)

    def soft_delete(self, batch_id: int, *, actor: str) -> Optional[dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                """
                UPDATE prb_import_batches
                SET enabled = FALSE,
                    modified_by = %s,
                    modified_on = NOW()
                WHERE id = %s AND enabled = TRUE
                RETURNING *
                """,
                [actor, batch_id],
            ).fetchone()
        return dict(row) if row else None
