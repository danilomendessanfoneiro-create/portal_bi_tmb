"""Active dataset resolution and BI filtering."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.active_dataset_service import (
    EMPTY_DATASET,
    ActiveDataset,
    ActiveDatasetService,
)


def test_resolve_prefers_manual_import_over_api():
    svc = ActiveDatasetService()
    with (
        patch.object(
            svc,
            "_latest_imported_batch",
            return_value={"id": 12, "file_name": "hoje.csv", "finished_on": None, "modified_on": None},
        ),
        patch.object(svc, "_count_deliveries", return_value=100),
        patch.object(svc, "_latest_api_sync_success", return_value={"id": 99, "job_id": "import_deliveries_daily"}),
    ):
        active = svc.resolve()
    assert active.source == "manual_import"
    assert active.batch_id == 12
    assert active.label == "hoje.csv"
    assert active.row_count == 100


def test_resolve_falls_back_to_api_when_no_manual():
    svc = ActiveDatasetService()
    with (
        patch.object(svc, "_latest_imported_batch", return_value=None),
        patch.object(
            svc,
            "_latest_api_sync_success",
            return_value={"id": 7, "job_id": "import_deliveries_daily", "finished_on": None, "started_on": None},
        ),
        patch.object(svc, "_count_deliveries", return_value=50),
    ):
        active = svc.resolve()
    assert active.source == "api_sync"
    assert active.sync_id == 7
    assert "Sync API #7" in active.label


def test_resolve_empty_when_nothing():
    svc = ActiveDatasetService()
    with (
        patch.object(svc, "_latest_imported_batch", return_value=None),
        patch.object(svc, "_latest_api_sync_success", return_value=None),
    ):
        active = svc.resolve()
    assert active.is_empty
    assert active.empty_reason


def test_list_for_bi_filters_by_batch(monkeypatch):
    from app.repositories import delivery_repository as dr

    captured: dict = {}

    def fake_execute(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        mock = MagicMock()
        mock.fetchall.return_value = []
        return mock

    conn = MagicMock()
    conn.execute.side_effect = fake_execute
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr(dr, "get_connection", lambda: conn)

    active = ActiveDataset(source="manual_import", batch_id=42, label="x")
    DeliveryRepository = dr.DeliveryRepository
    DeliveryRepository().list_for_bi(active=active, restrict_to_active_dataset=True)
    assert "dataset_batch_id = %s" in captured["sql"]
    assert "enabled = TRUE" in captured["sql"]
    assert captured["params"] == [42]


def test_list_for_bi_empty_dataset_returns_no_rows(monkeypatch):
    from app.repositories.delivery_repository import DeliveryRepository

    rows = DeliveryRepository().list_for_bi(active=EMPTY_DATASET, restrict_to_active_dataset=True)
    assert rows == []


def test_remember_skips_api_when_manual_exists():
    svc = ActiveDatasetService()
    with (
        patch.object(svc, "_latest_imported_batch", return_value={"id": 1}),
        patch("app.services.active_dataset_service.get_connection") as gc,
    ):
        svc.remember(source="api_sync", actor="worker", sync_id=9, label="x")
        gc.assert_not_called()
