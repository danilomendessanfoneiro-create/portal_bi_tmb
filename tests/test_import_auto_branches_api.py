"""API schema: auto_created_branches on import batches."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.api.routers.imports import _to_out


def test_to_out_includes_auto_created_branches():
    fake_batch = {
        "id": 99,
        "file_name": "x.csv",
        "file_ext": ".csv",
        "file_size_bytes": 1,
        "file_mtime": None,
        "status": "validated_ok",
        "total_rows": 1,
        "valid_rows": 1,
        "error_rows": 0,
        "rows_processed": 0,
        "rows_inserted": 0,
        "rows_updated": 0,
        "progress_pct": 0,
        "validation_errors": [],
        "started_on": None,
        "finished_on": None,
        "duration_ms": None,
        "error_message": None,
        "report_job_status": None,
        "report_job_message": None,
        "created_by": "admin",
        "created_on": None,
    }
    with patch("app.api.routers.imports.ImportRepository") as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.list_auto_branches.return_value = [
            {
                "branch": "TMB NOVA",
                "login": "nova",
                "user_id": 42,
                "created_on": None,
            }
        ]
        mock_repo_cls.return_value = mock_repo
        out = _to_out(fake_batch)

    assert len(out.auto_created_branches) == 1
    assert out.auto_created_branches[0].branch == "TMB NOVA"
    assert out.auto_created_branches[0].login == "nova"
    assert out.auto_created_branches[0].user_id == 42


def test_to_out_empty_auto_branches():
    fake_batch = {
        "id": 100,
        "file_name": "y.csv",
        "file_ext": ".csv",
        "file_size_bytes": 1,
        "status": "imported",
        "total_rows": 0,
        "valid_rows": 0,
        "error_rows": 0,
        "rows_processed": 0,
        "rows_inserted": 0,
        "rows_updated": 0,
        "progress_pct": 0,
        "validation_errors": [],
    }
    with patch("app.api.routers.imports.ImportRepository") as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.list_auto_branches.return_value = []
        mock_repo_cls.return_value = mock_repo
        out = _to_out(fake_batch)
    assert out.auto_created_branches == []
