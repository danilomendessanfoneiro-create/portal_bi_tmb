"""Integration run logs (prb_integration_logs)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from app.repositories.base import get_connection


class IntegrationLogRepository:
    def start(
        self,
        *,
        job_id: str,
        business_date: Optional[date],
        filter_start: Optional[date],
        filter_end: Optional[date],
        actor: str,
    ) -> int:
        sql = """
            INSERT INTO prb_integration_logs (
                job_id, business_date, status, started_on, filter_start, filter_end,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, 'running', NOW(), %s, %s, %s, NOW(), %s, NOW(), TRUE
            ) RETURNING id
        """
        with get_connection() as conn:
            row = conn.execute(sql, [job_id, business_date, filter_start, filter_end, actor, actor]).fetchone()
        return int(row["id"])

    def finish(
        self,
        log_id: int,
        *,
        status: str,
        pages_processed: int = 0,
        rows_inserted: int = 0,
        rows_updated: int = 0,
        error_count: int = 0,
        error_message: Optional[str] = None,
        actor: str = "worker",
    ) -> None:
        sql = """
            UPDATE prb_integration_logs SET
                status = %s,
                finished_on = NOW(),
                duration_ms = GREATEST(0, EXTRACT(EPOCH FROM (NOW() - started_on)) * 1000)::int,
                pages_processed = %s,
                rows_inserted = %s,
                rows_updated = %s,
                error_count = %s,
                error_message = %s,
                modified_by = %s,
                modified_on = NOW()
            WHERE id = %s
        """
        with get_connection() as conn:
            conn.execute(
                sql,
                [
                    status,
                    pages_processed,
                    rows_inserted,
                    rows_updated,
                    error_count,
                    error_message,
                    actor,
                    log_id,
                ],
            )
