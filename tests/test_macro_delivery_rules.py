"""Paridade das regras calcConsolidada.vb."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from app.services.macro_delivery_rules import (
    RULE_VERSION,
    STATUS_PRAZO_ATRASO,
    STATUS_PRAZO_DEPOIS_AMANHA,
    STATUS_PRAZO_FUTURO,
    STATUS_PRAZO_VENCENDO_AMANHA,
    STATUS_PRAZO_VENCENDO_HOJE,
    aplicar_regras_macros,
    classificar_status_prazo,
    excluir_status_entregue,
)
from limpeza import processar_planilha


def test_rule_version_consolidada():
    assert RULE_VERSION == "calc-consolidada-v1"


def test_classificar_status_prazo_faixas():
    hoje = date(2026, 7, 30)
    assert classificar_status_prazo(hoje - timedelta(days=1), hoje) == STATUS_PRAZO_ATRASO
    assert classificar_status_prazo(hoje, hoje) == STATUS_PRAZO_VENCENDO_HOJE
    assert classificar_status_prazo(hoje + timedelta(days=1), hoje) == STATUS_PRAZO_VENCENDO_AMANHA
    assert classificar_status_prazo(hoje + timedelta(days=2), hoje) == STATUS_PRAZO_DEPOIS_AMANHA
    assert classificar_status_prazo(hoje + timedelta(days=5), hoje) == STATUS_PRAZO_FUTURO
    assert classificar_status_prazo(None, hoje) == ""


def test_excluir_status_entregue():
    df = pd.DataFrame(
        {
            "nro_entrega": ["1", "2", "3"],
            "status": ["ENTREGUE", "EM ROTA", "entregue"],
        }
    )
    out = excluir_status_entregue(df)
    assert len(out) == 1
    assert out.iloc[0]["nro_entrega"] == "2"


def test_aplicar_regras_macros_consolidada_parity():
    hoje = date(2026, 7, 30)
    df = pd.DataFrame(
        {
            "nro_entrega": ["a", "b", "c"],
            "status": ["EM ROTA", "PENDENTE", "ENTREGUE"],
            "cliente": ["DEST OK", "DEST OK", "DEST ENT"],
            "dt_prazo_atual": [
                pd.Timestamp("2026-07-29"),
                pd.Timestamp("2026-07-30"),
                pd.Timestamp("2026-07-20"),
            ],
            "dt_agendamento": [
                pd.Timestamp("2026-08-10"),
                pd.Timestamp("2026-08-10"),
                pd.Timestamp("2026-08-10"),
            ],
            "dt_entrega": [pd.NaT, pd.NaT, pd.Timestamp("2026-07-28")],
            "dt_cancelamento": [pd.NaT, pd.NaT, pd.NaT],
        }
    )
    out = aplicar_regras_macros(df, data_referencia=hoje)
    assert len(out) == 2
    assert "ENTREGUE" not in set(out["status"].astype(str).str.upper())
    assert list(out["retorno_filial"].unique()) == [""]
    assert out.iloc[0]["status_prazo"] == STATUS_PRAZO_ATRASO
    assert bool(out.iloc[0]["atrasado"]) is True
    assert out.iloc[0]["prazo_considerado"].date() == date(2026, 7, 29)
    assert out.iloc[1]["status_prazo"] == STATUS_PRAZO_VENCENDO_HOJE
    assert bool(out.iloc[1]["vence_hoje"]) is True


def test_processar_planilha_exclui_entregue():
    from pathlib import Path

    csv_path = Path("dados/entregas_relatorio.csv")
    if not csv_path.is_file():
        return
    df = processar_planilha(str(csv_path), data_referencia=date.today())
    if "status" in df.columns and not df.empty:
        assert not (df["status"].astype(str).str.strip().str.upper() == "ENTREGUE").any()
