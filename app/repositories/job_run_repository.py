"""Job run persistence (prb_job_runs)."""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Optional

from app.repositories.base import get_connection


class JobRunRepository:
    def has_success(self, job_id: str, business_date: date) -> bool:
        sql = """
            SELECT 1 FROM prb_job_runs
            WHERE job_id = %s AND business_date = %s AND status = 'success' AND enabled = TRUE
            LIMIT 1
        """
        with get_connection() as conn:
            row = conn.execute(sql, [job_id, business_date]).fetchone()
        return row is not None

    def start(
        self,
        *,
        job_id: str,
        business_date: date,
        actor: str = "worker",
    ) -> int:
        sql = """
            INSERT INTO prb_job_runs (
                job_id, business_date, status, started_on,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, 'running', NOW(),
                %s, NOW(), %s, NOW(), TRUE
            )
            RETURNING id
        """
        with get_connection() as conn:
            row = conn.execute(sql, [job_id, business_date, actor, actor]).fetchone()
        return int(row["id"])

    def finish(
        self,
        run_id: int,
        *,
        status: str,
        message: str = "",
        metrics: Optional[dict[str, Any]] = None,
        artifact_path: Optional[str] = None,
        actor: str = "worker",
    ) -> Optional[dict[str, Any]]:
        payload = dict(metrics or {})
        error_step = payload.get("step") or payload.get("error_step")
        sql = """
            UPDATE prb_job_runs SET
                status = %s,
                finished_on = NOW(),
                duration_ms = GREATEST(
                    0,
                    FLOOR(EXTRACT(EPOCH FROM (NOW() - started_on)) * 1000)
                )::int,
                error_step = %s,
                message = %s,
                metrics_json = %s,
                artifact_path = %s,
                modified_by = %s,
                modified_on = NOW()
            WHERE id = %s
            RETURNING *
        """
        with get_connection() as conn:
            row = conn.execute(
                sql,
                [
                    status,
                    str(error_step) if error_step else None,
                    message or None,
                    json.dumps(payload, ensure_ascii=False),
                    artifact_path,
                    actor,
                    run_id,
                ],
            ).fetchone()
        return dict(row) if row else None
