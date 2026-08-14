"""US-001: migration 041 run_weekdays defaults."""

from __future__ import annotations

from app.config import settings


def test_migration_041_adds_run_weekdays_without_dropping_frequency():
    path = settings.migrations_dir / "041_add_job_run_weekdays.sql"
    sql = path.read_text(encoding="utf-8")
    assert "run_weekdays SMALLINT[]" in sql
    assert "{1,2,3,4,5,6}" in sql
    assert "prb_job_settings_audit" in sql
    assert "DROP COLUMN" not in sql.upper()
    assert "fetch_tmselite_spreadsheet" in sql
    assert "report_branch_daily" in sql
    assert "report_client_daily" in sql
    assert "report_managerial" in sql
    assert "import_deliveries_daily" in sql
    assert "import_deliveries_initial" in sql
    assert "enabled = FALSE" in sql
    assert "'05:00'" in sql
    assert "'08:00'" in sql


def test_migration_041_applied_defaults():
    from app.repositories.base import get_connection

    with get_connection() as conn:
        cols = conn.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'prb_job_settings' AND column_name = 'run_weekdays'
            """
        ).fetchone()
        assert cols is not None
        audit = conn.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'prb_job_settings_audit' AND column_name = 'run_weekdays'
            """
        ).fetchone()
        assert audit is not None
        freq = conn.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'prb_job_settings' AND column_name = 'frequency'
            """
        ).fetchone()
        assert freq is not None
        rows = conn.execute(
            """
            SELECT job_id, local_time, enabled, run_weekdays
            FROM prb_job_settings
            WHERE job_id IN (
                'fetch_tmselite_spreadsheet',
                'report_branch_daily',
                'report_client_daily',
                'report_managerial',
                'import_deliveries_daily',
                'import_deliveries_initial'
            )
            ORDER BY job_id
            """
        ).fetchall()
    by_id = {r["job_id"]: r for r in rows}
    tms = by_id["fetch_tmselite_spreadsheet"]
    assert tms["local_time"] == "05:00"
    assert tms["enabled"] is False
    assert list(tms["run_weekdays"]) == [1, 2, 3, 4, 5, 6]
    for job_id in ("report_branch_daily", "report_client_daily", "report_managerial"):
        row = by_id[job_id]
        assert row["local_time"] == "08:00"
        assert row["enabled"] is False
        assert list(row["run_weekdays"]) == [1, 2, 3, 4, 5, 6]
    for job_id in ("import_deliveries_daily", "import_deliveries_initial"):
        assert by_id[job_id]["enabled"] is False
