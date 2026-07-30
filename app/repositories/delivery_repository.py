"""Deliveries persistence (prb_deliveries)."""

from __future__ import annotations

import json
from typing import Any, Optional

from app.integrations.tmselite.models import DeliveryRecord
from app.repositories.base import get_connection


class DeliveryRepository:
    def upsert_many(
        self,
        records: list[DeliveryRecord],
        *,
        actor: str,
        source: str = "api",
    ) -> tuple[int, int]:
        inserted = 0
        updated = 0
        sql = """
            INSERT INTO prb_deliveries (
                remessa_numero, nro_entrega, nota_fiscal, cliente, filial, cidade_entrega, uf_entrega,
                status, valor_total, qtde_volumes, dt_prazo_atual, dt_agendamento, dt_entrega, dt_cancelamento,
                motivo_cancelamento, motivo_atraso, nome_recebedor, dt_cadastro, motorista, remetente,
                cidade_remetente, uf_remetente, peso_taxado, peso_informado, raw_json, synced_at, source,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s::jsonb, NOW(), %s,
                %s, NOW(), %s, NOW(), TRUE
            )
            ON CONFLICT (remessa_numero) DO UPDATE SET
                nro_entrega = EXCLUDED.nro_entrega,
                nota_fiscal = EXCLUDED.nota_fiscal,
                cliente = EXCLUDED.cliente,
                filial = EXCLUDED.filial,
                cidade_entrega = EXCLUDED.cidade_entrega,
                uf_entrega = EXCLUDED.uf_entrega,
                status = EXCLUDED.status,
                valor_total = EXCLUDED.valor_total,
                qtde_volumes = EXCLUDED.qtde_volumes,
                dt_prazo_atual = EXCLUDED.dt_prazo_atual,
                dt_agendamento = EXCLUDED.dt_agendamento,
                dt_entrega = EXCLUDED.dt_entrega,
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
                modified_by = EXCLUDED.modified_by,
                modified_on = NOW(),
                enabled = TRUE
            RETURNING (xmax = 0) AS inserted
        """
        with get_connection() as conn:
            for rec in records:
                raw = json.dumps(rec.raw_json) if rec.raw_json is not None else None
                row = conn.execute(
                    sql,
                    [
                        rec.remessa_numero,
                        rec.nro_entrega,
                        rec.nota_fiscal,
                        rec.cliente,
                        rec.filial,
                        rec.cidade_entrega,
                        rec.uf_entrega,
                        rec.status,
                        rec.valor_total,
                        rec.qtde_volumes,
                        rec.dt_prazo_atual,
                        rec.dt_agendamento,
                        rec.dt_entrega,
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
                        actor,
                        actor,
                    ],
                ).fetchone()
                if row and row.get("inserted"):
                    inserted += 1
                else:
                    updated += 1
        return inserted, updated

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

    def list_for_bi(self, *, include_disabled: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT * FROM prb_deliveries"
        if not include_disabled:
            sql += " WHERE enabled = TRUE"
        sql += " ORDER BY remessa_numero"
        with get_connection() as conn:
            rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

    def count_enabled(self) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM prb_deliveries WHERE enabled = TRUE"
            ).fetchone()
        return int(row["total"]) if row else 0
