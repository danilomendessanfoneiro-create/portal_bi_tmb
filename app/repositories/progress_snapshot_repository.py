"""Persistence for Progressão snapshots (per manual import batch)."""

from __future__ import annotations

from typing import Any, Optional

from app.repositories.base import get_connection


class ProgressSnapshotRepository:
    def get_run_by_batch_id(self, import_batch_id: int) -> Optional[dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM prb_progress_snapshot_run
                WHERE import_batch_id = %s AND enabled = TRUE
                LIMIT 1
                """,
                [import_batch_id],
            ).fetchone()
        return dict(row) if row else None

    def insert_run(
        self,
        *,
        import_batch_id: int,
        row_count: int,
        source: str,
        rule_version: str,
        actor: str,
        notes: Optional[str] = None,
        captured_at: Optional[Any] = None,
    ) -> int:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO prb_progress_snapshot_run (
                    import_batch_id, captured_at, source, row_count, rule_version, notes,
                    created_by, created_on, modified_by, modified_on, enabled
                ) VALUES (
                    %s, COALESCE(%s::timestamptz, NOW()), %s, %s, %s, %s,
                    %s, NOW(), %s, NOW(), TRUE
                )
                RETURNING id
                """,
                [
                    import_batch_id,
                    captured_at,
                    source,
                    row_count,
                    rule_version,
                    notes,
                    actor,
                    actor,
                ],
            ).fetchone()
        return int(row["id"])

    def delete_run_by_batch_id(self, import_batch_id: int) -> Optional[int]:
        """Hard delete (CASCADE items) to allow recreate under UNIQUE(import_batch_id)."""
        with get_connection() as conn:
            row = conn.execute(
                """
                DELETE FROM prb_progress_snapshot_run
                WHERE import_batch_id = %s
                RETURNING id
                """,
                [import_batch_id],
            ).fetchone()
        return int(row["id"]) if row else None

    def insert_items(
        self,
        *,
        snapshot_run_id: int,
        rows: list[dict[str, Any]],
        actor: str,
    ) -> int:
        if not rows:
            return 0
        sql = """
            INSERT INTO prb_progress_snapshot_item (
                snapshot_run_id, nro_entrega, remessa_numero, status, status_prazo, filial, cliente,
                cliente_conta, cnpj_cliente, cidade_entrega, uf_entrega, motorista, valor_total,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, NOW(), %s, NOW(), TRUE
            )
            ON CONFLICT (snapshot_run_id, nro_entrega) DO NOTHING
        """
        inserted = 0
        with get_connection() as conn:
            for r in rows:
                result = conn.execute(
                    sql,
                    [
                        snapshot_run_id,
                        r["nro_entrega"],
                        r.get("remessa_numero"),
                        r["status"],
                        r.get("status_prazo"),
                        r.get("filial"),
                        r.get("cliente"),
                        r.get("cliente_conta"),
                        r.get("cnpj_cliente"),
                        r.get("cidade_entrega"),
                        r.get("uf_entrega"),
                        r.get("motorista"),
                        r.get("valor_total"),
                        actor,
                        actor,
                    ],
                )
                if result.rowcount:
                    inserted += 1
        return inserted

    def list_runs(
        self,
        *,
        date_from: Any,
        date_to: Any,
    ) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, import_batch_id, captured_at, source, row_count, rule_version
                FROM prb_progress_snapshot_run
                WHERE enabled = TRUE
                  AND captured_at::date >= %s
                  AND captured_at::date <= %s
                ORDER BY captured_at ASC, id ASC
                """,
                [date_from, date_to],
            ).fetchall()
        return [dict(r) for r in rows]

    def list_filter_values(
        self,
        *,
        run_ids: list[int],
        filiais: Optional[list[str]] = None,
    ) -> dict[str, list[str]]:
        if not run_ids:
            return {"filiais": [], "clientes": [], "cidades": [], "statuses": []}
        where = ["enabled = TRUE", "snapshot_run_id = ANY(%s)"]
        params: list[Any] = [list(run_ids)]
        if filiais:
            where.append("filial = ANY(%s)")
            params.append(list(filiais))
        where_sql = " AND ".join(where)
        with get_connection() as conn:
            fil = conn.execute(
                f"SELECT DISTINCT filial FROM prb_progress_snapshot_item WHERE {where_sql} AND filial IS NOT NULL ORDER BY 1",
                params,
            ).fetchall()
            cli = conn.execute(
                f"SELECT DISTINCT cliente_conta FROM prb_progress_snapshot_item WHERE {where_sql} AND cliente_conta IS NOT NULL AND BTRIM(cliente_conta) <> '' ORDER BY 1",
                params,
            ).fetchall()
            cid = conn.execute(
                f"SELECT DISTINCT cidade_entrega FROM prb_progress_snapshot_item WHERE {where_sql} AND cidade_entrega IS NOT NULL ORDER BY 1",
                params,
            ).fetchall()
            stt = conn.execute(
                f"SELECT DISTINCT status_prazo FROM prb_progress_snapshot_item WHERE {where_sql} AND status_prazo IS NOT NULL AND status_prazo <> '' ORDER BY 1",
                params,
            ).fetchall()
        return {
            "filiais": [r["filial"] for r in fil],
            "clientes": [r["cliente_conta"] for r in cli],
            "cidades": [r["cidade_entrega"] for r in cid],
            "statuses": [r["status_prazo"] for r in stt],
        }

    def count_by_status_per_run(
        self,
        *,
        run_ids: list[int],
        filiais: Optional[list[str]] = None,
        clientes: Optional[list[str]] = None,
        cidades: Optional[list[str]] = None,
        statuses: Optional[list[str]] = None,
        busca: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        if not run_ids:
            return []
        where = ["i.enabled = TRUE", "i.snapshot_run_id = ANY(%s)"]
        params: list[Any] = [list(run_ids)]
        if filiais:
            where.append("i.filial = ANY(%s)")
            params.append(list(filiais))
        if clientes:
            where.append("i.cliente_conta = ANY(%s)")
            params.append(list(clientes))
        if cidades:
            where.append("i.cidade_entrega = ANY(%s)")
            params.append(list(cidades))
        if statuses:
            where.append("i.status_prazo = ANY(%s)")
            params.append(list(statuses))
        if busca and busca.strip():
            term = f"%{busca.strip()}%"
            where.append(
                "(i.cliente_conta ILIKE %s OR i.cliente ILIKE %s OR i.nro_entrega ILIKE %s)"
            )
            params.extend([term, term, term])
        sql = f"""
            SELECT i.snapshot_run_id, i.status_prazo, COUNT(*)::int AS qty
            FROM prb_progress_snapshot_item i
            WHERE {' AND '.join(where)}
            GROUP BY i.snapshot_run_id, i.status_prazo
            ORDER BY i.snapshot_run_id, i.status_prazo
        """
        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def count_distinct_nro_entrega(
        self,
        *,
        run_ids: list[int],
        filiais: Optional[list[str]] = None,
        clientes: Optional[list[str]] = None,
        cidades: Optional[list[str]] = None,
        statuses: Optional[list[str]] = None,
        busca: Optional[str] = None,
    ) -> int:
        """União de nro_entrega nos runs (sem duplicar entre uploads)."""
        if not run_ids:
            return 0
        where = ["i.enabled = TRUE", "i.snapshot_run_id = ANY(%s)"]
        params: list[Any] = [list(run_ids)]
        if filiais:
            where.append("i.filial = ANY(%s)")
            params.append(list(filiais))
        if clientes:
            where.append("i.cliente_conta = ANY(%s)")
            params.append(list(clientes))
        if cidades:
            where.append("i.cidade_entrega = ANY(%s)")
            params.append(list(cidades))
        if statuses:
            where.append("i.status_prazo = ANY(%s)")
            params.append(list(statuses))
        if busca and busca.strip():
            term = f"%{busca.strip()}%"
            where.append(
                "(i.cliente_conta ILIKE %s OR i.cliente ILIKE %s OR i.nro_entrega ILIKE %s)"
            )
            params.extend([term, term, term])
        sql = f"""
            SELECT COUNT(DISTINCT i.nro_entrega)::int AS qty
            FROM prb_progress_snapshot_item i
            WHERE {' AND '.join(where)}
        """
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row["qty"]) if row else 0

    def count_delivered_between_runs(
        self,
        *,
        prev_run_id: int,
        curr_run_id: int,
        filiais: Optional[list[str]] = None,
        clientes: Optional[list[str]] = None,
        cidades: Optional[list[str]] = None,
        statuses: Optional[list[str]] = None,
        busca: Optional[str] = None,
    ) -> int:
        """nro_entrega in prev and absent in curr (with filters applied to prev set)."""
        where_prev = ["p.enabled = TRUE", "p.snapshot_run_id = %s"]
        params: list[Any] = [prev_run_id, curr_run_id]
        if filiais:
            where_prev.append("p.filial = ANY(%s)")
            params.append(list(filiais))
        if clientes:
            where_prev.append("p.cliente_conta = ANY(%s)")
            params.append(list(clientes))
        if cidades:
            where_prev.append("p.cidade_entrega = ANY(%s)")
            params.append(list(cidades))
        if statuses:
            where_prev.append("p.status_prazo = ANY(%s)")
            params.append(list(statuses))
        if busca and busca.strip():
            term = f"%{busca.strip()}%"
            where_prev.append(
                "(p.cliente_conta ILIKE %s OR p.cliente ILIKE %s OR p.nro_entrega ILIKE %s)"
            )
            params.extend([term, term, term])
        sql = f"""
            SELECT COUNT(*)::int AS qty
            FROM prb_progress_snapshot_item p
            WHERE {' AND '.join(where_prev)}
              AND NOT EXISTS (
                SELECT 1 FROM prb_progress_snapshot_item c
                WHERE c.enabled = TRUE
                  AND c.snapshot_run_id = %s
                  AND c.nro_entrega = p.nro_entrega
              )
        """
        # Fix param order: prev filters first, then curr_run_id for NOT EXISTS
        params = [prev_run_id]
        if filiais:
            params.append(list(filiais))
        if clientes:
            params.append(list(clientes))
        if cidades:
            params.append(list(cidades))
        if statuses:
            params.append(list(statuses))
        if busca and busca.strip():
            term = f"%{busca.strip()}%"
            params.extend([term, term, term])
        params.append(curr_run_id)
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row["qty"]) if row else 0

    def update_run_row_count(self, run_id: int, row_count: int, *, actor: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE prb_progress_snapshot_run
                SET row_count = %s, modified_by = %s, modified_on = NOW()
                WHERE id = %s
                """,
                [row_count, actor, run_id],
            )
