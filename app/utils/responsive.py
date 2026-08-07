"""Helpers de layout responsivo do BI (constantes + resumo de filtros)."""

from __future__ import annotations

from typing import Any

import streamlit as st

# Alturas Plotly: phone/tablet usam CSS de empilhamento; altura compacta ajuda o toque
CHART_HEIGHT_DESKTOP = 320
CHART_HEIGHT_COMPACT = 260
HIST_SERIES_HEIGHT_DESKTOP = 420
HIST_SERIES_HEIGHT_COMPACT = 280

# Limite de categorias no gráfico de barras (excesso via filtros/tabela)
CHART_CATEGORY_LIMIT = 12

# Colunas prioritárias em tabelas mobile (ordem)
OPERACIONAL_TABLE_COLS_PRIORITY = [
    "nota_fiscal",
    "cliente",
    "filial",
    "Situação",
    "dt_agendamento",
    "cidade_entrega",
]
HISTORICO_TABLE_COLS_PRIORITY = [
    "nota_fiscal",
    "cliente",
    "filial",
    "dias_atraso",
    "prazo_considerado",
    "valor_total",
    "cidade_entrega",
    "status",
    "status_prazo",
    "motorista",
]


def chart_height(*, compact: bool = False) -> int:
    return CHART_HEIGHT_COMPACT if compact else CHART_HEIGHT_DESKTOP


def hist_series_height(*, compact: bool = False) -> int:
    return HIST_SERIES_HEIGHT_COMPACT if compact else HIST_SERIES_HEIGHT_DESKTOP


def limit_chart_categories(df, *, y_col: str, value_col: str, limit: int = CHART_CATEGORY_LIMIT):
    """Mantém as N maiores categorias (já ordenadas ascending para barras horizontais)."""
    if df is None or df.empty or len(df) <= limit:
        return df
    return df.tail(limit)


def render_filter_chips(items: list[tuple[str, Any]]) -> None:
    """Resumo de filtros ativos (expander fechado)."""
    chips = []
    for label, value in items:
        if value is None or value == "" or value == [] or value == "Todas":
            continue
        if isinstance(value, (list, tuple)):
            if not value:
                continue
            text = ", ".join(str(v) for v in value[:3])
            if len(value) > 3:
                text += f" +{len(value) - 3}"
        else:
            text = str(value)
        chips.append(f'<span class="bi-filter-chip">{label}: {text}</span>')
    if chips:
        st.markdown(
            f'<div class="bi-filter-chips">{"".join(chips)}</div>',
            unsafe_allow_html=True,
        )
