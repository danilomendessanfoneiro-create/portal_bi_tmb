"""Deliveries persistence (prb_deliveries)."""

from __future__ import annotations

import json
from typing import Any, Optional

from app.integrations.tmselite.models import DeliveryRecord
from app.repositories.base import get_connection
from app.services.active_dataset_service import ActiveDataset, ActiveDatasetService


class DeliveryRepository:
    def upsert_many(
        self,
        records: list[DeliveryRecord],
        *,
        actor: str,
        source: str = "api",
        conn=None,
        dataset_batch_id: Optional[int] = None,
        dataset_sync_id: Optional[int] = None,
        dataset_source: Optional[str] = None,
    ) -> tuple[int, int]:
        if conn is not None:
            return self._upsert_many_on_conn(
                conn,
                records,
                actor=actor,
                source=source,
                dataset_batch_id=dataset_batch_id,
                dataset_sync_id=dataset_sync_id,
                dataset_source=dataset_source,
            )
        with get_connection() as owned:
            return self._upsert_many_on_conn(
                owned,
                records,
                actor=actor,
                source=source,
                dataset_batch_id=dataset_batch_id,
                dataset_sync_id=dataset_sync_id,
                dataset_source=dataset_source,
            )

    def _upsert_many_on_conn(
        self,
        conn,
        records: list[DeliveryRecord],
        *,
        actor: str,
        source: str,
        dataset_batch_id: Optional[int] = None,
        dataset_sync_id: Optional[int] = None,
        dataset_source: Optional[str] = None,
    ) -> tuple[int, int]:
        inserted = 0
        updated = 0
        # Manual: força batch e limpa sync. API: grava sync e preserva batch_id existente.
        if dataset_source == "manual_import" or dataset_batch_id is not None:
            ds_source = dataset_source or "manual_import"
            sql = """
                INSERT INTO prb_deliveries (
                    remessa_numero, nro_entrega, nota_fiscal, cliente, cliente_conta, filial, cidade_entrega,
                    uf_entrega, status, valor_total, qtde_volumes, dt_prazo_atual, dt_agendamento, dt_entrega,
                    dt_recebimento, dt_cancelamento, motivo_cancelamento, motivo_atraso, nome_recebedor,
                    dt_cadastro, motorista, remetente, cidade_remetente, uf_remetente, peso_taxado,
                    peso_informado, raw_json, synced_at, source, dataset_source, dataset_batch_id,
                    dataset_sync_id, created_by, created_on, modified_by, modified_on, enabled
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s::jsonb, NOW(), %s, %s, %s,
                    NULL, %s, NOW(), %s, NOW(), TRUE
                )
                ON CONFLICT (remessa_numero) DO UPDATE SET
                    nro_entrega = EXCLUDED.nro_entrega,
                    nota_fiscal = EXCLUDED.nota_fiscal,
                    cliente = EXCLUDED.cliente,
                    cliente_conta = EXCLUDED.cliente_conta,
                    filial = EXCLUDED.filial,
                    cidade_entrega = EXCLUDED.cidade_entrega,
                    uf_entrega = EXCLUDED.uf_entrega,
                    status = EXCLUDED.status,
                    valor_total = EXCLUDED.valor_total,
                    qtde_volumes = EXCLUDED.qtde_volumes,
                    dt_prazo_atual = EXCLUDED.dt_prazo_atual,
                    dt_agendamento = EXCLUDED.dt_agendamento,
                    dt_entrega = EXCLUDED.dt_entrega,
                    dt_recebimento = EXCLUDED.dt_recebimento,
                    dt_cancelamento = EXCLUDED.dt_cancelamento,
                    motivo_cancelamento = EXCLUDED.motivo_cancelamento,
                    motivo_atraso = EXCLUDED.motivo_atraso,
                    nome_recebedor = EXCLUDED.nome_recebedor,
                    dt_cadastro = EXCLUDED.dt_cadastro,
                    motorista = EXCLUDED.motorista,
                    remetente = EXCLUDED.remetente,
                    cidade_remetente = EXCLUDED.cidade_remetente,
                    uf_remetente = EXCLUDED.uf_remetente,
                    peso_taxado = EXCLUDED.peso_taxado,
                    peso_informado = EXCLUDED.peso_informado,
                    raw_json = EXCLUDED.raw_json,
                    synced_at = NOW(),
                    source = EXCLUDED.source,
                    dataset_source = EXCLUDED.dataset_source,
                    dataset_batch_id = EXCLUDED.dataset_batch_id,
                    dataset_sync_id = NULL,
                    modified_by = EXCLUDED.modified_by,
                    modified_on = NOW(),
                    enabled = TRUE
                RETURNING (xmax = 0) AS inserted
            """
            for rec in records:
                raw = json.dumps(rec.raw_json) if rec.raw_json is not None else None
                row = conn.execute(
                    sql,
                    self._row_params(
                        rec,
                        raw=raw,
                        source=source,
                        actor=actor,
                        dataset_source=ds_source,
                        dataset_batch_id=dataset_batch_id,
                    ),
                ).fetchone()
                if row and row.get("inserted"):
                    inserted += 1
                else:
                    updated += 1
            return inserted, updated

        # API sync path
        ds_source = dataset_source or "api_sync"
        sql = """
            INSERT INTO prb_deliveries (
                remessa_numero, nro_entrega, nota_fiscal, cliente, cliente_conta, filial, cidade_entrega,
                uf_entrega, status, valor_total, qtde_volumes, dt_prazo_atual, dt_agendamento, dt_entrega,
                dt_recebimento, dt_cancelamento, motivo_cancelamento, motivo_atraso, nome_recebedor,
                dt_cadastro, motorista, remetente, cidade_remetente, uf_remetente, peso_taxado,
                peso_informado, raw_json, synced_at, source, dataset_source, dataset_batch_id,
                dataset_sync_id, created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s::jsonb, NOW(), %s, %s, NULL,
                %s, %s, NOW(), %s, NOW(), TRUE
            )
            ON CONFLICT (remessa_numero) DO UPDATE SET
                nro_entrega = EXCLUDED.nro_entrega,
                nota_fiscal = EXCLUDED.nota_fiscal,
                cliente = EXCLUDED.cliente,
                cliente_conta = EXCLUDED.cliente_conta,
                filial = EXCLUDED.filial,
                cidade_entrega = EXCLUDED.cidade_entrega,
                uf_entrega = EXCLUDED.uf_entrega,
                status = EXCLUDED.status,
                valor_total = EXCLUDED.valor_total,
                qtde_volumes = EXCLUDED.qtde_volumes,
                dt_prazo_atual = EXCLUDED.dt_prazo_atual,
                dt_agendamento = EXCLUDED.dt_agendamento,
                dt_entrega = EXCLUDED.dt_entrega,
                dt_recebimento = EXCLUDED.dt_recebimento,
                dt_cancelamento = EXCLUDED.dt_cancelamento,
                motivo_cancelamento = EXCLUDED.motivo_cancelamento,
                motivo_atraso = EXCLUDED.motivo_atraso,
                nome_recebedor = EXCLUDED.nome_recebedor,
                dt_cadastro = EXCLUDED.dt_cadastro,
                motorista = EXCLUDED.motorista,
                remetente = EXCLUDED.remetente,
                cidade_remetente = EXCLUDED.cidade_remetente,
                uf_remetente = EXCLUDED.uf_remetente,
                peso_taxado = EXCLUDED.peso_taxado,
                peso_informado = EXCLUDED.peso_informado,
                raw_json = EXCLUDED.raw_json,
                synced_at = NOW(),
                source = EXCLUDED.source,
                dataset_sync_id = EXCLUDED.dataset_sync_id,
                dataset_source = CASE
                    WHEN prb_deliveries.dataset_batch_id IS NOT NULL THEN prb_deliveries.dataset_source
                    ELSE EXCLUDED.dataset_source
                END,
                modified_by = EXCLUDED.modified_by,
                modified_on = NOW(),
                enabled = TRUE
            RETURNING (xmax = 0) AS inserted
        """
        for rec in records:
            raw = json.dumps(rec.raw_json) if rec.raw_json is not None else None
            row = conn.execute(
                sql,
                self._row_params_api(
                    rec,
                    raw=raw,
                    source=source,
                    actor=actor,
                    dataset_source=ds_source,
                    dataset_sync_id=dataset_sync_id,
                ),
            ).fetchone()
            if row and row.get("inserted"):
                inserted += 1
            else:
                updated += 1
        return inserted, updated

    @staticmethod
    def _row_params(
        rec: DeliveryRecord,
        *,
        raw: Optional[str],
        source: str,
        actor: str,
        dataset_source: str,
        dataset_batch_id: Optional[int],
    ) -> list[Any]:
        return [
            rec.remessa_numero,
            rec.nro_entrega,
            rec.nota_fiscal,
            rec.cliente,
            rec.cliente_conta,
            rec.filial,
            rec.cidade_entrega,
            rec.uf_entrega,
            rec.status,
            rec.valor_total,
            rec.qtde_volumes,
            rec.dt_prazo_atual,
            rec.dt_agendamento,
            rec.dt_entrega,
            rec.dt_recebimento,
            rec.dt_cancelamento,
            rec.motivo_cancelamento,
            rec.motivo_atraso,
            rec.nome_recebedor,
            rec.dt_cadastro,
            rec.motorista,
            rec.remetente,
            rec.cidade_remetente,
            rec.uf_remetente,
            rec.peso_taxado,
            rec.peso_informado,
            raw,
            source,
            dataset_source,
            dataset_batch_id,
            actor,
            actor,
        ]

    @staticmethod
    def _row_params_api(
        rec: DeliveryRecord,
        *,
        raw: Optional[str],
        source: str,
        actor: str,
        dataset_source: str,
        dataset_sync_id: Optional[int],
    ) -> list[Any]:
        return [
            rec.remessa_numero,
            rec.nro_entrega,
            rec.nota_fiscal,
            rec.cliente,
            rec.cliente_conta,
            rec.filial,
            rec.cidade_entrega,
            rec.uf_entrega,
            rec.status,
            rec.valor_total,
            rec.qtde_volumes,
            rec.dt_prazo_atual,
            rec.dt_agendamento,
            rec.dt_entrega,
            rec.dt_recebimento,
            rec.dt_cancelamento,
            rec.motivo_cancelamento,
            rec.motivo_atraso,
            rec.nome_recebedor,
            rec.dt_cadastro,
            rec.motorista,
            rec.remetente,
            rec.cidade_remetente,
            rec.uf_remetente,
            rec.peso_taxado,
            rec.peso_informado,
            raw,
            source,
            dataset_source,
            dataset_sync_id,
            actor,
            actor,
        ]

    def delete_all(self) -> int:
        with get_connection() as conn:
            rows = conn.execute("DELETE FROM prb_deliveries RETURNING id").fetchall()
        return len(rows)

    def disable_by_source(self, source: str, *, actor: str) -> int:
        with get_connection() as conn:
            rows = conn.execute(
                """
                UPDATE prb_deliveries
                SET enabled = FALSE, modified_by = %s, modified_on = NOW()
                WHERE source = %s AND enabled = TRUE
                RETURNING id
                """,
                [actor, source],
            ).fetchall()
        return len(rows)

    def list_for_bi(
        self,
        *,
        include_disabled: bool = False,
        active: Optional[ActiveDataset] = None,
        restrict_to_active_dataset: bool = True,
    ) -> list[dict[str, Any]]:
        dataset = active
        if restrict_to_active_dataset and dataset is None:
            dataset = ActiveDatasetService().resolve()

        clauses: list[str] = []
        params: list[Any] = []
        if not include_disabled:
            clauses.append("enabled = TRUE")

        if restrict_to_active_dataset:
            if dataset is None or dataset.is_empty:
                return []
            if dataset.source == "manual_import" and dataset.batch_id is not None:
                clauses.append("dataset_batch_id = %s")
                params.append(dataset.batch_id)
            elif dataset.source == "api_sync" and dataset.sync_id is not None:
                clauses.append("dataset_sync_id = %s")
                params.append(dataset.sync_id)
            else:
                return []

        sql = "SELECT * FROM prb_deliveries"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY remessa_numero"
        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def count_enabled(self) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM prb_deliveries WHERE enabled = TRUE"
            ).fetchone()
        return int(row["total"]) if row else 0
