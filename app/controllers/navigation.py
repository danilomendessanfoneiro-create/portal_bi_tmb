"""Painel de filtros compartilhado do BI (Operacional e Histórico)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal, Optional

import streamlit as st

from app.services.access_scope_service import ViewerContext

BiFilterMode = Literal["operacional", "historico"]

# Seleções de drill dos gráficos (persistentes; limpas pelo botão do painel)
DRILL_FILIAL_KEY = "bi_drill_filial"
DRILL_SITUACAO_KEY = "bi_drill_situacao"
CHART_BAR_KEY = "grafico_barras"
CHART_PIE_KEY = "grafico_situacao"

WINDOW_OPTIONS = {
    "7 dias": 7,
    "15 dias": 15,
    "30 dias": 30,
    "60 dias": 60,
    "90 dias": 90,
    "Personalizado": None,
}


@dataclass
class BiDashboardFilters:
    busca: str
    filtro_filial: list[Any]
    filtro_cliente: list[Any]
    filtro_cidade: list[Any]
    situacao: str = "Todas"
    filtro_periodo: Optional[tuple] = None
    tolerancia: int = 0
    date_from: Optional[date] = None
    date_to: Optional[date] = None


SidebarFilters = BiDashboardFilters


def _k(mode: BiFilterMode, name: str) -> str:
    """Keys por aba — Streamlit renderiza as duas tabs no mesmo run."""
    return f"bi_filtro_{mode}_{name}"


def _read_list(key: str) -> list[Any]:
    value = st.session_state.get(key, [])
    return list(value) if value else []


def clear_chart_drills() -> None:
    for chave in [CHART_BAR_KEY, CHART_PIE_KEY, DRILL_FILIAL_KEY, DRILL_SITUACAO_KEY]:
        st.session_state.pop(chave, None)


def resolve_historico_window(hoje: date) -> tuple[date, date]:
    """Lê a janela do histórico no session_state (mesmo com painel recolhido)."""
    key_janela = _k("historico", "janela")
    key_periodo = _k("historico", "periodo_hist")
    if key_janela not in st.session_state:
        st.session_state[key_janela] = "7 dias"
    janela = st.session_state.get(key_janela, "7 dias")
    days = WINDOW_OPTIONS.get(janela, 7)
    if days is None:
        if key_periodo not in st.session_state:
            st.session_state[key_periodo] = (hoje - timedelta(days=29), hoje)
        periodo = st.session_state.get(key_periodo)
        if isinstance(periodo, tuple) and len(periodo) == 2:
            return periodo[0], periodo[1]
        return hoje, hoje
    return hoje - timedelta(days=days - 1), hoje


def _render_common_fields(
    *,
    mode: BiFilterMode,
    viewer: ViewerContext,
    filiais: list[Any],
    clientes: list[Any],
    cidades: list[Any],
) -> None:
    st.text_input(
        "Buscar por NF ou cliente",
        placeholder="Ex: 509656 ou Stella Doro",
        key=_k(mode, "busca"),
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        if viewer.is_admin:
            st.multiselect("Filial", filiais, key=_k(mode, "filial"))
        else:
            st.text_input(
                "Filial",
                value=viewer.branch or "",
                disabled=True,
                help="Filial fixa conforme o perfil do usuário.",
                key=_k(mode, "filial_readonly"),
            )
            st.session_state[_k(mode, "filial")] = [viewer.branch] if viewer.branch else []
    with c2:
        st.multiselect("Cliente", clientes, key=_k(mode, "cliente"))
    with c3:
        st.multiselect("Cidade", cidades, key=_k(mode, "cidade"))


def _render_operacional_extras(periodo_bounds: Optional[tuple[date, date]]) -> None:
    mode: BiFilterMode = "operacional"
    key_sit = _k(mode, "situacao")
    key_tol = _k(mode, "tolerancia")
    key_per = _k(mode, "periodo")
    if key_sit not in st.session_state:
        st.session_state[key_sit] = "Todas"
    if key_tol not in st.session_state:
        st.session_state[key_tol] = 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox(
            "Situação",
            ["Todas", "Em aberto", "Vencendo hoje", "Em dia"],
            key=key_sit,
        )
    with c2:
        if periodo_bounds:
            data_min, data_max = periodo_bounds
            if key_per not in st.session_state:
                st.session_state[key_per] = (data_min, data_max)
            st.date_input(
                "Prazo considerado entre",
                min_value=data_min,
                max_value=data_max,
                help="Filtra pela data de prazo considerada.",
                key=key_per,
            )
        else:
            st.caption("Sem datas de prazo disponíveis.")
    with c3:
        st.slider(
            "Tolerância extra (dias)",
            min_value=0,
            max_value=15,
            help="Simula o impacto de dias extras de prazo.",
            key=key_tol,
        )

    if st.button(
        "Limpar seleção dos gráficos",
        icon=":material/ink_eraser:",
        width="content",
        key=_k(mode, "clear_charts"),
    ):
        clear_chart_drills()
        st.rerun()


def _render_historico_extras(hoje: date) -> None:
    mode: BiFilterMode = "historico"
    key_janela = _k(mode, "janela")
    key_periodo = _k(mode, "periodo_hist")
    c1, c2 = st.columns([2, 3])
    with c1:
        if key_janela not in st.session_state:
            st.session_state[key_janela] = "7 dias"
        st.selectbox("Janela do histórico", list(WINDOW_OPTIONS.keys()), key=key_janela)

    days = WINDOW_OPTIONS.get(st.session_state.get(key_janela, "7 dias"))
    if days is None:
        with c2:
            if key_periodo not in st.session_state:
                st.session_state[key_periodo] = (hoje - timedelta(days=29), hoje)
            st.date_input(
                "Período personalizado",
                max_value=hoje,
                key=key_periodo,
            )


def _collect_filters(
    *,
    viewer: ViewerContext,
    mode: BiFilterMode,
    hoje: Optional[date],
) -> BiDashboardFilters:
    busca = str(st.session_state.get(_k(mode, "busca"), "") or "")
    if viewer.is_admin:
        filtro_filial = _read_list(_k(mode, "filial"))
    else:
        filtro_filial = [viewer.branch] if viewer.branch else []

    situacao = "Todas"
    tolerancia = 0
    filtro_periodo = None
    if mode == "operacional":
        situacao = str(st.session_state.get(_k(mode, "situacao"), "Todas") or "Todas")
        tolerancia = int(st.session_state.get(_k(mode, "tolerancia"), 0) or 0)
        periodo = st.session_state.get(_k(mode, "periodo"))
        filtro_periodo = periodo if isinstance(periodo, tuple) and len(periodo) == 2 else None

    date_from = date_to = None
    if mode == "historico" and hoje is not None:
        date_from, date_to = resolve_historico_window(hoje)

    return BiDashboardFilters(
        busca=busca,
        filtro_filial=filtro_filial,
        filtro_cliente=_read_list(_k(mode, "cliente")),
        filtro_cidade=_read_list(_k(mode, "cidade")),
        situacao=situacao,
        filtro_periodo=filtro_periodo,
        tolerancia=tolerancia,
        date_from=date_from,
        date_to=date_to,
    )


def render_bi_filters_panel(
    *,
    viewer: ViewerContext,
    mode: BiFilterMode,
    filiais: list[Any],
    clientes: list[Any],
    cidades: list[Any],
    periodo_bounds: Optional[tuple[date, date]] = None,
    hoje: Optional[date] = None,
) -> BiDashboardFilters:
    """Painel expansível no topo — widgets sempre montados (estado persiste recolhido)."""
    with st.expander("Filtros", expanded=False, icon=":material/filter_alt:", key=_k(mode, "expander")):
        _render_common_fields(
            mode=mode,
            viewer=viewer,
            filiais=filiais,
            clientes=clientes,
            cidades=cidades,
        )
        if mode == "operacional":
            st.markdown("---")
            _render_operacional_extras(periodo_bounds)
        else:
            st.markdown("---")
            assert hoje is not None
            _render_historico_extras(hoje)

    return _collect_filters(viewer=viewer, mode=mode, hoje=hoje)
