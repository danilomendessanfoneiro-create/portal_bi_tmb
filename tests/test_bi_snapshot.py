"""Tests for BI historical snapshot capture."""

from __future__ import annotations

from datetime import date

import pandas as pd

from app.services.bi_snapshot_service import RULE_VERSION, dataframe_to_overdue_rows


def test_dataframe_to_overdue_rows_uses_nro_as_remessa():
    df = pd.DataFrame(
        [
            {
                "nro_entrega": "123",
                "nota_fiscal": "NF1",
                "filial": "TMB VIANA",
                "cliente": "ACME",
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
    assert rows[0]["dias_atraso"] == 3


def test_rule_version_constant():
    assert RULE_VERSION == "macros-v1"


def test_skips_rows_without_key():
    df = pd.DataFrame([{"cliente": "X", "filial": "Y"}])
    assert dataframe_to_overdue_rows(df) == []
