"""Tests for BI historical snapshot capture."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd

from app.services.bi_snapshot_service import (
    RULE_VERSION,
    BiSnapshotService,
    dataframe_to_overdue_rows,
)


def test_dataframe_to_overdue_rows_uses_nro_as_remessa():
    df = pd.DataFrame(
        [
            {
                "nro_entrega": "123",
                "nota_fiscal": "NF1",
                "filial": "TMB VIANA",
                "cliente": "ACME",
                "cliente_conta": "NINFA",
                "cidade_entrega": "Vitória",
                "dias_atraso": 3,
                "valor_total": 10.5,
                "status_prazo": "01_ATRASO",
            }
        ]
    )
    rows = dataframe_to_overdue_rows(df)
    assert len(rows) == 1
    assert rows[0]["remessa_numero"] == "123"
    assert rows[0]["filial"] == "TMB VIANA"
    assert rows[0]["cliente_conta"] == "NINFA"
    assert rows[0]["dias_atraso"] == 3


def test_rule_version_constant():
    assert RULE_VERSION == "macros-v1"


def test_skips_rows_without_key():
    df = pd.DataFrame([{"cliente": "X", "filial": "Y"}])
    assert dataframe_to_overdue_rows(df) == []


def test_list_overdue_for_day_empty():
    repo = MagicMock()
    repo.list_overdue_for_day.return_value = []
    svc = BiSnapshotService(repo=repo)
    out = svc.list_overdue_for_day(business_date=date(2026, 7, 31))
    assert out.empty
    repo.list_overdue_for_day.assert_called_once()
    kwargs = repo.list_overdue_for_day.call_args.kwargs
    assert kwargs["business_date"] == date(2026, 7, 31)


def test_list_overdue_for_day_passes_filters():
    repo = MagicMock()
    repo.list_overdue_for_day.return_value = [
        {
            "business_date": date(2026, 7, 31),
            "remessa_numero": "1",
            "nro_entrega": "1",
            "nota_fiscal": "NF-A",
            "filial": "SPO",
            "cliente": "ACME",
            "cidade_entrega": "SP",
            "uf_entrega": "SP",
            "status": "Em rota",
            "motorista": "João",
            "dias_atraso": 5,
            "valor_total": 100.0,
            "prazo_considerado": "2026-07-20",
            "status_prazo": "01_ATRASO",
        }
    ]
    svc = BiSnapshotService(repo=repo)
    out = svc.list_overdue_for_day(
        business_date=date(2026, 7, 31),
        filiais=["SPO"],
        clientes=["ACME"],
        cidades=["SP"],
        busca="NF",
    )
    assert len(out) == 1
    assert out.iloc[0]["filial"] == "SPO"
    assert out.iloc[0]["dias_atraso"] == 5
    kwargs = repo.list_overdue_for_day.call_args.kwargs
    assert kwargs["filiais"] == ["SPO"]
    assert kwargs["clientes"] == ["ACME"]
    assert kwargs["cidades"] == ["SP"]
    assert kwargs["busca"] == "NF"


def test_list_overdue_for_day_filial_scope_arg():
    """Perfil filial: controller passa branch_filter; service propaga filiais ao repo."""
    repo = MagicMock()
    repo.list_overdue_for_day.return_value = []
    svc = BiSnapshotService(repo=repo)
    svc.list_overdue_for_day(business_date=date(2026, 7, 1), filiais=["TMB VIANA"])
    assert repo.list_overdue_for_day.call_args.kwargs["filiais"] == ["TMB VIANA"]


def test_capture_replace_deletes_then_creates():
    repo = MagicMock()
    repo.delete_run_by_business_date.return_value = 10
    repo.get_run_by_business_date.return_value = None
    repo.insert_run.return_value = 11
    repo.insert_overdue_rows.return_value = 2
    svc = BiSnapshotService(repo=repo)
    df = pd.DataFrame(
        [
            {"nro_entrega": "1", "filial": "A", "dias_atraso": 1, "status_prazo": "01_ATRASO"},
            {"nro_entrega": "2", "filial": "B", "dias_atraso": 2, "status_prazo": "01_ATRASO"},
        ]
    )
    result = svc.capture_replace(date(2026, 7, 31), df, actor="admin")
    assert result.status == "replaced"
    assert result.rows == 2
    repo.delete_run_by_business_date.assert_called_once_with(date(2026, 7, 31))
    repo.insert_run.assert_called_once()
