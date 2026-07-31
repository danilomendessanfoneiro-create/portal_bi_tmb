"""Import column mapping coverage for delay/dashboard fields."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from app.services.csv_delivery_import_service import map_csv_row
from limpeza import COLUNAS_DATA, COLUNAS_UTEIS, selecionar_colunas, tratar_tipos


def test_dt_recebimento_mapped_from_spreadsheet_header():
    assert COLUNAS_UTEIS["Dt. Recebimento"] == "dt_recebimento"
    assert "dt_recebimento" in COLUNAS_DATA


def test_selecionar_colunas_keeps_dt_recebimento():
    df = pd.DataFrame(
        {
            "Nro. Entrega": ["1"],
            "Sigla Unidade Entrega": ["FILIAL A"],
            "Nome Pessoa Visita": ["Cliente"],
            "Dt. Prazo Atual": ["30/07/2026"],
            "Dt. Recebimento": ["29/12/2025 13:26"],
            "Dt. Entrega": ["-"],
            "Coluna Extra Ignorada": ["x"],
        }
    )
    out = selecionar_colunas(df)
    assert "dt_recebimento" in out.columns
    assert "Coluna Extra Ignorada" not in out.columns
    typed = tratar_tipos(out)
    assert typed.loc[0, "dt_recebimento"] == pd.Timestamp("2025-12-29 13:26:00")


def test_map_csv_row_persists_dt_recebimento():
    row = pd.Series(
        {
            "nro_entrega": "25329371",
            "dt_prazo_atual": datetime(2026, 7, 30),
            "dt_recebimento": datetime(2025, 12, 29, 13, 26),
            "dt_entrega": None,
            "filial": "TMB",
            "cliente": "CLI",
        }
    )
    rec = map_csv_row(row)
    assert rec.dt_recebimento == datetime(2025, 12, 29, 13, 26)
    assert rec.dt_entrega is None
