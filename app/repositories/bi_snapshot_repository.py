"""Persistence for BI historical overdue snapshots."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from app.repositories.base import get_connection


class BiSnapshotRepository:
    def get_run_by_business_date(self, business_date: date) -> Optional[dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM prb_bi_snapshot_run
                WHERE business_date = %s AND enabled = TRUE
                LIMIT 1
                """,
                [business_date],
            ).fetchone()
        return dict(row) if row else None

    def insert_run(
        self,
        *,
        business_date: date,
        total_overdue: int,
        total_value_overdue: Optional[float],
        source: str,
        rule_version: str,
        source_job_id: Optional[str],
        source_run_id: Optional[int],
        actor: str,
        captured_on: Optional[datetime] = None,
    ) -> int:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO prb_bi_snapshot_run (
                    business_date, captured_on, source_job_id, source_run_id, rule_version,
                    total_overdue, total_value_overdue, source,
                    created_by, created_on, modified_by, modified_on, enabled
                ) VALUES (
                    %s, COALESCE(%s, NOW()), %s, %s, %s,
                    %s, %s, %s,
                    %s, NOW(), %s, NOW(), TRUE
                )
                RETURNING id
                """,
                [
                    business_date,
                    captured_on,
                    source_job_id,
                    source_run_id,
                    rule_version,
                    total_overdue,
                    total_value_overdue,
                    source,
                    actor,
                    actor,
                ],
            ).fetchone()
        return int(row["id"])

    def insert_overdue_rows(
        self,
        *,
        snapshot_run_id: int,
        business_date: date,
        rows: list[dict[str, Any]],
        actor: str,
    ) -> int:
        if not rows:
            return 0
        sql = """
            INSERT INTO prb_bi_snapshot_overdue (
                snapshot_run_id, business_date, remessa_numero, nro_entrega, nota_fiscal,
                filial, cliente, cidade_entrega, uf_entrega, status, motorista, dias_atraso,
                valor_total, prazo_considerado, status_prazo,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, NOW(), %s, NOW(), TRUE
            )
            ON CONFLICT (snapshot_run_id, remessa_numero) DO NOTHING
        """
        inserted = 0
        with get_connection() as conn:
            for r in rows:
                result = conn.execute(
                    sql,
                    [
                        snapshot_run_id,
                        business_date,
                        r["remessa_numero"],
                        r.get("nro_entrega"),
                        r.get("nota_fiscal"),
                        r.get("filial"),
                        r.get("cliente"),
                        r.get("cidade_entrega"),
                        r.get("uf_entrega"),
                        r.get("status"),
                        r.get("motorista"),
                        r.get("dias_atraso"),
                        r.get("valor_total"),
                        r.get("prazo_considerado"),
                        r.get("status_prazo"),
                        actor,
                        actor,
                    ],
                )
                if result.rowcount:
                    inserted += 1
        return inserted

    def delete_demo_runs(self) -> int:
        with get_connection() as conn:
            rows = conn.execute(
                """
                DELETE FROM prb_bi_snapshot_run
                WHERE source = 'seed-demo'
                RETURNING id
                """
            ).fetchall()
        return len(rows)

    def delete_run_by_business_date(self, business_date: date) -> Optional[int]:
        """Remove o snapshot do dia (overdue via ON DELETE CASCADE)."""
        with get_connection() as conn:
            row = conn.execute(
                """
                DELETE FROM prb_bi_snapshot_run
                WHERE business_date = %s
                RETURNING id
                """,
                [business_date],
            ).fetchone()
        return int(row["id"]) if row else None

    def aggregate_overdue_by_day(
        self,
        *,
        date_from: date,
        date_to: date,
        filiais: Optional[list[str]] = None,
        clientes: Optional[list[str]] = None,
        cidades: Optional[list[str]] = None,
        busca: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        where = [
            "o.enabled = TRUE",
            "r.enabled = TRUE",
            "o.business_date >= %s",
            "o.business_date <= %s",
        ]
        params: list[Any] = [date_from, date_to]
        if filiais:
            where.append("o.filial = ANY(%s)")
            params.append(list(filiais))
        if clientes:
            where.append("o.cliente = ANY(%s)")
            params.append(list(clientes))
        if cidades:
            where.append("o.cidade_entrega = ANY(%s)")
            params.append(list(cidades))
        if busca and busca.strip():
            term = f"%{busca.strip()}%"
            where.append("(o.nota_fiscal ILIKE %s OR o.cliente ILIKE %s)")
            params.extend([term, term])

        sql = f"""
            SELECT o.business_date AS business_date, COUNT(*)::int AS overdue_count
            FROM prb_bi_snapshot_overdue o
            INNER JOIN prb_bi_snapshot_run r ON r.id = o.snapshot_run_id
            WHERE {' AND '.join(where)}
            GROUP BY o.business_date
            ORDER BY o.business_date
        """
        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def list_overdue_for_day(
        self,
        *,
        business_date: date,
        filiais: Optional[list[str]] = None,
        clientes: Optional[list[str]] = None,
        cidades: Optional[list[str]] = None,
        busca: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        where = [
            "o.enabled = TRUE",
            "r.enabled = TRUE",
            "o.business_date = %s",
        ]
        params: list[Any] = [business_date]
        if filiais:
            where.append("o.filial = ANY(%s)")
            params.append(list(filiais))
        if clientes:
            where.append("o.cliente = ANY(%s)")
            params.append(list(clientes))
        if cidades:
            where.append("o.cidade_entrega = ANY(%s)")
            params.append(list(cidades))
        if busca and busca.strip():
            term = f"%{busca.strip()}%"
            where.append("(o.nota_fiscal ILIKE %s OR o.cliente ILIKE %s)")
            params.extend([term, term])

        sql = f"""
            SELECT
                o.business_date, o.remessa_numero, o.nro_entrega, o.nota_fiscal,
                o.filial, o.cliente, o.cidade_entrega, o.uf_entrega,
                o.status, o.motorista, o.dias_atraso, o.valor_total,
                o.prazo_considerado, o.status_prazo
            FROM prb_bi_snapshot_overdue o
            INNER JOIN prb_bi_snapshot_run r ON r.id = o.snapshot_run_id
            WHERE {' AND '.join(where)}
            ORDER BY o.dias_atraso DESC NULLS LAST, o.nota_fiscal
        """
        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def list_filter_values(
        self,
        *,
        date_from: date,
        date_to: date,
        filiais: Optional[list[str]] = None,
    ) -> dict[str, list[str]]:
        where = [
            "o.enabled = TRUE",
            "o.business_date >= %s",
            "o.business_date <= %s",
        ]
        params: list[Any] = [date_from, date_to]
        if filiais:
            where.append("o.filial = ANY(%s)")
            params.append(list(filiais))
        where_sql = " AND ".join(where)
        with get_connection() as conn:
            fil = conn.execute(
                f"SELECT DISTINCT filial FROM prb_bi_snapshot_overdue o WHERE {where_sql} AND filial IS NOT NULL ORDER BY 1",
                params,
            ).fetchall()
            cli = conn.execute(
                f"SELECT DISTINCT cliente FROM prb_bi_snapshot_overdue o WHERE {where_sql} AND cliente IS NOT NULL ORDER BY 1",
                params,
            ).fetchall()
            cid = conn.execute(
                f"SELECT DISTINCT cidade_entrega FROM prb_bi_snapshot_overdue o WHERE {where_sql} AND cidade_entrega IS NOT NULL ORDER BY 1",
                params,
            ).fetchall()
        return {
            "filiais": [r["filial"] for r in fil],
            "clientes": [r["cliente"] for r in cli],
            "cidades": [r["cidade_entrega"] for r in cid],
        }
