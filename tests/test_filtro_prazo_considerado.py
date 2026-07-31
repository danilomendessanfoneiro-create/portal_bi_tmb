"""Testes do filtro Prazo considerado (Operacional)."""

from datetime import date

import pandas as pd

from app.controllers.dashboard_controller import _filtrar_prazo_considerado
from app.controllers.navigation import _parse_prazo_periodo


def _df():
    return pd.DataFrame(
        {
            "atrasado": [True, True, True, False, True],
            "prazo_considerado": pd.to_datetime(
                [
                    "2026-07-20",
                    "2026-07-31",
                    "2026-08-05",
                    "2026-07-31",  # não atrasado
                    None,
                ]
            ),
            "remessa": ["a", "b", "c", "d", "e"],
        }
    )


def test_sem_filtro_retorna_tudo():
    df = _df()
    out = _filtrar_prazo_considerado(df, None, None)
    assert len(out) == len(df)


def test_intervalo_completo_so_atrasados_no_range():
    out = _filtrar_prazo_considerado(_df(), date(2026, 7, 20), date(2026, 7, 31))
    assert set(out["remessa"]) == {"a", "b"}


def test_somente_data_inicial():
    out = _filtrar_prazo_considerado(_df(), date(2026, 7, 31), None)
    assert set(out["remessa"]) == {"b", "c"}


def test_datas_iguais_dia_exato():
    out = _filtrar_prazo_considerado(_df(), date(2026, 7, 31), date(2026, 7, 31))
    assert list(out["remessa"]) == ["b"]


def test_exclui_prazo_nulo_e_nao_atrasado():
    out = _filtrar_prazo_considerado(_df(), date(2026, 1, 1), date(2026, 12, 31))
    assert "d" not in set(out["remessa"])
    assert "e" not in set(out["remessa"])


def test_parse_periodo_vazio():
    assert _parse_prazo_periodo(()) is None
    assert _parse_prazo_periodo(None) is None


def test_parse_periodo_so_inicial():
    assert _parse_prazo_periodo((date(2026, 7, 31),)) == (date(2026, 7, 31),)
    assert _parse_prazo_periodo(date(2026, 7, 31)) == (date(2026, 7, 31),)


def test_parse_periodo_range():
    assert _parse_prazo_periodo((date(2026, 7, 1), date(2026, 7, 31))) == (
        date(2026, 7, 1),
        date(2026, 7, 31),
    )
