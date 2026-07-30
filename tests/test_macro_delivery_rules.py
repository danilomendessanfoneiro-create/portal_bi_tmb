"""Paridade das regras das macros Excel (calc1/calc2)."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from app.services.macro_delivery_rules import (
    CLIENTES_EXCLUIR_MACROS,
    STATUS_PRAZO_ATRASO,
    STATUS_PRAZO_DEPOIS_AMANHA,
    STATUS_PRAZO_FUTURO,
    STATUS_PRAZO_VENCENDO_AMANHA,
    STATUS_PRAZO_VENCENDO_HOJE,
    aplicar_regras_macros,
    classificar_status_prazo,
    excluir_clientes_macros,
)


def test_classificar_status_prazo_faixas():
    hoje = date(2026, 7, 30)
    assert classificar_status_prazo(hoje - timedelta(days=1), hoje) == STATUS_PRAZO_ATRASO
    assert classificar_status_prazo(hoje, hoje) == STATUS_PRAZO_VENCENDO_HOJE
    assert classificar_status_prazo(hoje + timedelta(days=1), hoje) == STATUS_PRAZO_VENCENDO_AMANHA
    assert classificar_status_prazo(hoje + timedelta(days=2), hoje) == STATUS_PRAZO_DEPOIS_AMANHA
    assert classificar_status_prazo(hoje + timedelta(days=5), hoje) == STATUS_PRAZO_FUTURO
    assert classificar_status_prazo(None, hoje) == ""


def test_exclui_clientes_macros():
    df = pd.DataFrame(
        {
            "cliente": [
                "NINFA INDUSTRIA DE ALIMENTOS LTDA",
                "OUTRO CLIENTE LTDA",
                "prediLECTA ALIMENTOS LTDA",
            ],
            "nro_entrega": ["1", "2", "3"],
        }
    )
    out = excluir_clientes_macros(df)
    assert len(out) == 1
    assert out.iloc[0]["cliente"] == "OUTRO CLIENTE LTDA"
    assert "NINFA INDUSTRIA DE ALIMENTOS LTDA" in CLIENTES_EXCLUIR_MACROS


def test_aplicar_regras_macros_excel_parity():
    hoje = date(2026, 7, 30)
    df = pd.DataFrame(
        {
            "nro_entrega": ["a", "b", "c"],
            "cliente": ["CLIENTE OK", "CLIENTE OK", "NINFA INDUSTRIA DE ALIMENTOS LTDA"],
            "dt_prazo_atual": [
                pd.Timestamp("2026-07-29"),
                pd.Timestamp("2026-07-30"),
                pd.Timestamp("2026-07-20"),
            ],
            "dt_agendamento": [
                pd.Timestamp("2026-08-10"),  # maior que prazo — NÃO deve puxar vencimento
                pd.Timestamp("2026-08-10"),
                pd.Timestamp("2026-08-10"),
            ],
            "dt_entrega": [pd.Timestamp("2026-07-28"), pd.NaT, pd.NaT],
            "dt_cancelamento": [pd.NaT, pd.NaT, pd.NaT],
        }
    )
    out = aplicar_regras_macros(df, data_referencia=hoje)
    assert len(out) == 2  # NINFA excluída
    assert list(out["retorno_filial"].unique()) == [""]
    assert out.iloc[0]["status_prazo"] == STATUS_PRAZO_ATRASO
    assert out.iloc[0]["atrasado"] is True or bool(out.iloc[0]["atrasado"]) is True
    # Mesmo com agendamento futuro e já entregue, atraso segue só dt_prazo_atual
    assert out.iloc[0]["prazo_considerado"].date() == date(2026, 7, 29)
    assert out.iloc[1]["status_prazo"] == STATUS_PRAZO_VENCENDO_HOJE
    assert bool(out.iloc[1]["vence_hoje"]) is True
