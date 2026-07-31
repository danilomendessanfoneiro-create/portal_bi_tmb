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
from limpeza import processar_planilha


def test_classificar_status_prazo_faixas():
    hoje = date(2026, 7, 30)
    assert classificar_status_prazo(hoje - timedelta(days=1), hoje) == STATUS_PRAZO_ATRASO
    assert classificar_status_prazo(hoje, hoje) == STATUS_PRAZO_VENCENDO_HOJE
    assert classificar_status_prazo(hoje + timedelta(days=1), hoje) == STATUS_PRAZO_VENCENDO_AMANHA
    assert classificar_status_prazo(hoje + timedelta(days=2), hoje) == STATUS_PRAZO_DEPOIS_AMANHA
    assert classificar_status_prazo(hoje + timedelta(days=5), hoje) == STATUS_PRAZO_FUTURO
    assert classificar_status_prazo(None, hoje) == ""


def test_exclui_clientes_macros_por_cliente_conta():
    """calc1 filtra a coluna Excel Cliente (= cliente_conta), não o destinatário."""
    df = pd.DataFrame(
        {
            "cliente_conta": [
                "NINFA INDUSTRIA DE ALIMENTOS LTDA",
                "OUTRO CLIENTE LTDA",
                "prediLECTA ALIMENTOS LTDA",
            ],
            "cliente": ["DEST A", "DEST B", "DEST C"],
            "nro_entrega": ["1", "2", "3"],
        }
    )
    out = excluir_clientes_macros(df)
    assert len(out) == 1
    assert out.iloc[0]["cliente_conta"] == "OUTRO CLIENTE LTDA"
    assert "NINFA INDUSTRIA DE ALIMENTOS LTDA" in CLIENTES_EXCLUIR_MACROS


def test_exclui_clientes_macros_por_remetente_com_alias_ninfa():
    """Nome Remetente usa variação NINFA ALIMENTOS LTDA."""
    df = pd.DataFrame(
        {
            "cliente": ["DESTINATARIO A", "DESTINATARIO B", "DESTINATARIO C"],
            "remetente": [
                "STELLA DORO ALIMENTOS LTDA",
                "NINFA ALIMENTOS LTDA",
                "OUTRO REMETENTE",
            ],
            "nro_entrega": ["1", "2", "3"],
        }
    )
    out = excluir_clientes_macros(df)
    assert len(out) == 1
    assert out.iloc[0]["cliente"] == "DESTINATARIO C"


def test_nao_exclui_pelo_destinatario():
    """Destinatário com nome parecido não deve ser usado como chave de exclusão."""
    df = pd.DataFrame(
        {
            "cliente": ["NINFA INDUSTRIA DE ALIMENTOS LTDA"],
            "cliente_conta": ["CAMIL ALIMENTOS S.A."],
            "remetente": ["CAMIL ALIMENTOS SA"],
            "nro_entrega": ["1"],
        }
    )
    out = excluir_clientes_macros(df)
    assert len(out) == 1


def test_aplicar_regras_macros_excel_parity():
    hoje = date(2026, 7, 30)
    df = pd.DataFrame(
        {
            "nro_entrega": ["a", "b", "c"],
            "cliente": ["DEST OK", "DEST OK", "DEST NINFA"],
            "cliente_conta": ["CLIENTE OK", "CLIENTE OK", "NINFA INDUSTRIA DE ALIMENTOS LTDA"],
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
            "dt_entrega": [pd.Timestamp("2026-07-28"), pd.NaT, pd.NaT],
            "dt_cancelamento": [pd.NaT, pd.NaT, pd.NaT],
        }
    )
    out = aplicar_regras_macros(df, data_referencia=hoje)
    assert len(out) == 2  # NINFA excluída via cliente_conta
    assert list(out["retorno_filial"].unique()) == [""]
    assert out.iloc[0]["status_prazo"] == STATUS_PRAZO_ATRASO
    assert out.iloc[0]["atrasado"] is True or bool(out.iloc[0]["atrasado"]) is True
    assert out.iloc[0]["prazo_considerado"].date() == date(2026, 7, 29)
    assert out.iloc[1]["status_prazo"] == STATUS_PRAZO_VENCENDO_HOJE
    assert bool(out.iloc[1]["vence_hoje"]) is True


def test_processar_planilha_exclui_conta_excel_e_conta_atrasos():
    """Garante que a planilha real aplica exclusão da coluna Cliente (~paridade macro)."""
    from pathlib import Path

    csv_path = Path("dados/entregas_relatorio.csv")
    if not csv_path.is_file():
        return
    df = processar_planilha(str(csv_path), data_referencia=date.today())
    assert int(df["atrasado"].sum()) < 500
    # Contas excluídas não podem permanecer via cliente_conta
    if "cliente_conta" in df.columns:
        left = set(df["cliente_conta"].astype(str).str.strip().str.upper())
        assert not (left & {c.upper() for c in CLIENTES_EXCLUIR_MACROS})
