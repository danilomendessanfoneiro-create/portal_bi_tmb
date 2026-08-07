"""Tests for Progressão snapshot capture (STATUS PRAZO pós-macros)."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pandas as pd

from app.services.macro_delivery_rules import (
    STATUS_PRAZO_ATRASO,
    STATUS_PRAZO_VENCENDO_HOJE,
)
from app.services.progress_snapshot_service import (
    RULE_VERSION,
    STATUS_PRAZO_SEM,
    ProgressSnapshotService,
    prepare_progress_frame,
    rows_to_progress_items,
)


def test_rule_version_constant():
    assert RULE_VERSION == "calc-consolidada-v1"


def test_prepare_progress_frame_excludes_entregue_and_sets_status_prazo():
    hoje = date(2026, 8, 7)
    df = pd.DataFrame(
        [
            {
                "nro_entrega": "1",
                "status": "EM ROTA",
                "dt_prazo_atual": pd.Timestamp("2026-08-06"),
                "filial": "A",
            },
            {
                "nro_entrega": "2",
                "status": "ENTREGUE",
                "dt_prazo_atual": pd.Timestamp("2026-08-01"),
                "filial": "B",
            },
            {
                "nro_entrega": "3",
                "status": "PENDENTE",
                "dt_prazo_atual": pd.Timestamp("2026-08-07"),
                "filial": "C",
            },
        ]
    )
    out = prepare_progress_frame(df, data_referencia=hoje)
    assert set(out["nro_entrega"].astype(str)) == {"1", "3"}
    by_nro = out.set_index("nro_entrega")["status_prazo"].to_dict()
    assert by_nro["1"] == STATUS_PRAZO_ATRASO
    assert by_nro["3"] == STATUS_PRAZO_VENCENDO_HOJE


def test_rows_to_progress_items_status_prazo_fallback_and_dedupe():
    rows = [
        {
            "nro_entrega": "100",
            "remessa_numero": "R100",
            "status": "EM ROTA",
            "status_prazo": STATUS_PRAZO_ATRASO,
            "filial": "SPO",
            "cliente": "ACME",
            "cnpj_cliente": "12.345.678/0001-90",
            "valor_total": 10.5,
        },
        {
            "nro_entrega": "100",
            "status": "PENDENTE",
            "status_prazo": STATUS_PRAZO_VENCENDO_HOJE,
            "filial": "SPO",
        },
        {
            "nro_entrega": "200",
            "status": "EM ROTA",
            "filial": "CWB",
            "cnpj_cliente": "123",
        },
        {"nro_entrega": None, "status": "X"},
    ]
    items = rows_to_progress_items(rows)
    assert len(items) == 2
    by_nro = {i["nro_entrega"]: i for i in items}
    assert by_nro["100"]["status"] == "EM ROTA"
    assert by_nro["100"]["status_prazo"] == STATUS_PRAZO_ATRASO
    assert by_nro["100"]["cnpj_cliente"] == "12345678000190"
    assert by_nro["200"]["status_prazo"] == STATUS_PRAZO_SEM


def test_rows_to_progress_items_from_dataframe():
    df = pd.DataFrame(
        [
            {"nro_entrega": "1", "status": "ABERTO", "status_prazo": STATUS_PRAZO_ATRASO},
            {"nro_entrega": "2", "status": "EM ROTA", "status_prazo": ""},
        ]
    )
    items = rows_to_progress_items(df)
    assert {i["nro_entrega"] for i in items} == {"1", "2"}
    assert items[1]["status_prazo"] == STATUS_PRAZO_SEM


def test_capture_for_batch_applies_macros():
    repo = MagicMock()
    repo.get_run_by_batch_id.return_value = None
    repo.insert_run.return_value = 77
    repo.insert_items.return_value = 1
    svc = ProgressSnapshotService(repo=repo)
    hoje = date(2026, 8, 7)
    result = svc.capture_for_batch(
        55,
        [
            {
                "nro_entrega": "1",
                "status": "ENTREGUE",
                "dt_prazo_atual": hoje - timedelta(days=2),
                "filial": "A",
            },
            {
                "nro_entrega": "2",
                "status": "EM ROTA",
                "dt_prazo_atual": hoje - timedelta(days=1),
                "filial": "B",
            },
        ],
        actor="admin",
        captured_at=hoje,
    )
    assert result.status == "created"
    assert result.run_id == 77
    assert result.rows == 1
    kwargs = repo.insert_run.call_args.kwargs
    assert kwargs["import_batch_id"] == 55
    assert kwargs["rule_version"] == RULE_VERSION
    assert kwargs["row_count"] == 1
    items = repo.insert_items.call_args.kwargs["rows"]
    assert len(items) == 1
    assert items[0]["nro_entrega"] == "2"
    assert items[0]["status_prazo"] == STATUS_PRAZO_ATRASO
    assert items[0]["status"] == "EM ROTA"


def test_capture_for_batch_skips_existing():
    repo = MagicMock()
    repo.get_run_by_batch_id.return_value = {"id": 9, "row_count": 3}
    svc = ProgressSnapshotService(repo=repo)
    result = svc.capture_for_batch(10, [{"nro_entrega": "1", "status": "X"}], actor="a")
    assert result.status == "skipped"
    assert result.run_id == 9
    assert result.rows == 3
    repo.insert_run.assert_not_called()


def test_capture_for_batch_replace_deletes_existing():
    repo = MagicMock()
    repo.get_run_by_batch_id.return_value = {"id": 9, "row_count": 3}
    repo.insert_run.return_value = 11
    repo.insert_items.return_value = 1
    svc = ProgressSnapshotService(repo=repo)
    result = svc.capture_for_batch(
        10,
        [
            {
                "nro_entrega": "1",
                "status": "EM ROTA",
                "dt_prazo_atual": date(2026, 8, 1),
            }
        ],
        actor="a",
        replace=True,
        captured_at="2026-08-01T12:00:00",
    )
    assert result.status == "replaced"
    repo.delete_run_by_batch_id.assert_called_once_with(10)
    assert repo.insert_run.call_args.kwargs["captured_at"] == "2026-08-01T12:00:00"


def test_capture_for_batch_failed_on_repo_error():
    repo = MagicMock()
    repo.get_run_by_batch_id.return_value = None
    repo.insert_run.side_effect = RuntimeError("db down")
    svc = ProgressSnapshotService(repo=repo)
    result = svc.capture_for_batch(
        1,
        [{"nro_entrega": "1", "status": "EM ROTA", "dt_prazo_atual": date(2026, 8, 1)}],
        actor="a",
        captured_at=date(2026, 8, 7),
    )
    assert result.status == "failed"
    assert "db down" in result.message


def test_rows_to_progress_items_accepts_status_entrega():
    items = rows_to_progress_items(
        [{"nro_entrega": "9", "status_entrega": "EM ROTA", "filial": "A"}]
    )
    assert items[0]["status"] == "EM ROTA"
    assert items[0]["status_prazo"] == STATUS_PRAZO_SEM
