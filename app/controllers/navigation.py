"""Painel de filtros compartilhado do BI (Operacional e Histórico)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Literal, Optional

import streamlit as st

from app.services.access_scope_service import ViewerContext

BiFilterMode = Literal["operacional", "historico", "progressao"]


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
    filtro_status: list[Any]
    situacao: str = "Todas"
    # Prazo considerado: () = off; (ini,) = só início; (ini, fim) = intervalo inclusive
    filtro_periodo: Optional[tuple] = None
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
    status_opts: Optional[list[Any]] = None,
) -> None:
    st.text_input(
        "Buscar por NF, cliente indústria ou destinatário",
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

    if status_opts is not None:
        status_label = "Status prazo" if mode == "progressao" else "Status"
        st.multiselect(
            status_label,
            status_opts,
            key=_k(mode, "status"),
            help=(
                "Vazio = todos os STATUS PRAZO do período."
                if mode == "progressao"
                else "Vazio = comportamento padrão (sem filtrar por texto de status)."
            ),
        )


def _coerce_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _parse_prazo_periodo(raw: Any) -> Optional[tuple]:
    """Normaliza o valor do date_input range para (ini,), (ini, fim) ou None."""
    if raw is None or raw == () or raw == []:
        return None
    if isinstance(raw, datetime):
        return (raw.date(),)
    if isinstance(raw, date):
        return (raw,)
    if isinstance(raw, (tuple, list)):
        datas = [_coerce_date(x) for x in raw]
        datas = [d for d in datas if d is not None]
        if not datas:
            return None
        if len(datas) == 1:
            return (datas[0],)
        return (datas[0], datas[1])
    return None


def _render_operacional_extras(periodo_bounds: Optional[tuple[date, date]]) -> None:
    mode: BiFilterMode = "operacional"
    key_sit = _k(mode, "situacao")
    key_per = _k(mode, "periodo_v2")
    if key_sit not in st.session_state:
        st.session_state[key_sit] = "Todas"
    if key_per not in st.session_state:
        # Vazio = filtro desligado (não pré-selecionar min–max do dataset)
        st.session_state[key_per] = ()

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox(
            "Situação",
            ["Todas", "Em aberto", "Vencendo hoje", "Em dia"],
            key=key_sit,
        )
    with c2:
        if periodo_bounds:
            data_min, data_max = periodo_bounds
            st.date_input(
                "Prazo considerado",
                min_value=data_min,
                max_value=data_max,
                format="DD/MM/YYYY",
                help=(
                    "Intervalo pela data do prazo (Dt. Prazo Atual). "
                    "Com as duas datas: atrasados no intervalo (inclusive). "
                    "Só a inicial: atrasados com prazo ≥ inicial. "
                    "Datas iguais: exatamente aquele dia."
                ),
                key=key_per,
            )
        else:
            st.caption("Sem datas de prazo disponíveis.")

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


def _render_progressao_extras(hoje: date) -> None:
    mode: BiFilterMode = "progressao"
    key_janela = _k(mode, "janela")
    key_periodo = _k(mode, "periodo_prog")
    c1, c2 = st.columns([2, 3])
    with c1:
        if key_janela not in st.session_state:
            st.session_state[key_janela] = "7 dias"
        st.selectbox("Janela da progressão", list(WINDOW_OPTIONS.keys()), key=key_janela)

    days = WINDOW_OPTIONS.get(st.session_state.get(key_janela, "7 dias"))
    if days is None:
        with c2:
            if key_periodo not in st.session_state:
                st.session_state[key_periodo] = (hoje - timedelta(days=6), hoje)
            st.date_input(
                "Período personalizado",
                max_value=hoje,
                key=key_periodo,
            )


def resolve_progressao_window(hoje: date) -> tuple[date, date]:
    key_janela = _k("progressao", "janela")
    key_periodo = _k("progressao", "periodo_prog")
    if key_janela not in st.session_state:
        st.session_state[key_janela] = "7 dias"
    janela = st.session_state.get(key_janela, "7 dias")
    days = WINDOW_OPTIONS.get(janela, 7)
    if days is None:
        if key_periodo not in st.session_state:
            st.session_state[key_periodo] = (hoje - timedelta(days=6), hoje)
        periodo = st.session_state.get(key_periodo)
        if isinstance(periodo, tuple) and len(periodo) == 2:
            return periodo[0], periodo[1]
        return hoje, hoje
    return hoje - timedelta(days=days - 1), hoje


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
    filtro_periodo = None
    if mode == "operacional":
        situacao = str(st.session_state.get(_k(mode, "situacao"), "Todas") or "Todas")
        filtro_periodo = _parse_prazo_periodo(st.session_state.get(_k(mode, "periodo_v2")))

    date_from = date_to = None
    if mode == "historico" and hoje is not None:
        date_from, date_to = resolve_historico_window(hoje)
    elif mode == "progressao" and hoje is not None:
        date_from, date_to = resolve_progressao_window(hoje)

    return BiDashboardFilters(
        busca=busca,
        filtro_filial=filtro_filial,
        filtro_cliente=_read_list(_k(mode, "cliente")),
        filtro_cidade=_read_list(_k(mode, "cidade")),
        filtro_status=_read_list(_k(mode, "status")),
        situacao=situacao,
        filtro_periodo=filtro_periodo,
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
    status_opts: Optional[list[Any]] = None,
    periodo_bounds: Optional[tuple[date, date]] = None,
    hoje: Optional[date] = None,
) -> BiDashboardFilters:
    """Painel expansível no topo — widgets sempre montados (estado persiste recolhido)."""
    from app.utils.responsive import render_filter_chips

    with st.expander("Filtros", expanded=False, icon=":material/filter_alt:", key=_k(mode, "expander")):
        _render_common_fields(
            mode=mode,
            viewer=viewer,
            filiais=filiais,
            clientes=clientes,
            cidades=cidades,
            status_opts=status_opts if status_opts is not None else [],
        )
        if mode == "operacional":
            st.markdown("---")
            _render_operacional_extras(periodo_bounds)
        elif mode == "historico":
            st.markdown("---")
            assert hoje is not None
            _render_historico_extras(hoje)
        else:
            st.markdown("---")
            assert hoje is not None
            _render_progressao_extras(hoje)

    filters = _collect_filters(viewer=viewer, mode=mode, hoje=hoje)

    chip_items: list[tuple[str, Any]] = [
        ("Busca", filters.busca),
        ("Filial", filters.filtro_filial if viewer.is_admin else None),
        ("Cliente", filters.filtro_cliente),
        ("Cidade", filters.filtro_cidade),
        ("Status prazo" if mode == "progressao" else "Status", filters.filtro_status),
    ]
    if mode == "operacional":
        chip_items.append(("Situação", filters.situacao))
        if filters.filtro_periodo:
            if len(filters.filtro_periodo) >= 2:
                chip_items.append(
                    ("Prazo", f"{filters.filtro_periodo[0]} → {filters.filtro_periodo[1]}")
                )
            else:
                chip_items.append(("Prazo ≥", filters.filtro_periodo[0]))
    else:
        if filters.date_from and filters.date_to:
            chip_items.append(("Janela", f"{filters.date_from} → {filters.date_to}"))
    render_filter_chips(chip_items)
    return filters
