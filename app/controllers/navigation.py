"""Sidebar do BI: apenas filtros (menu fica no Admin React)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd
import streamlit as st

from app.services.access_scope_service import ViewerContext


@dataclass
class SidebarFilters:
    busca: str
    filtro_filial: list[Any]
    filtro_cliente: list[Any]
    filtro_cidade: list[Any]
    situacao: str
    filtro_periodo: Optional[tuple]
    tolerancia: int


def render_sidebar_nav(df: pd.DataFrame, viewer: ViewerContext) -> SidebarFilters:
    """Renderiza só os filtros do BI na sidebar."""
    with st.sidebar:
        st.markdown("**Filtros**")
        busca = st.text_input(
            "Buscar por NF ou cliente",
            placeholder="Ex: 509656 ou Stella Doro",
        )

        if viewer.is_admin:
            filiais_disponiveis = sorted(df["filial"].dropna().unique())
            filtro_filial = st.multiselect("Filial", filiais_disponiveis)
        else:
            st.text_input(
                "Filial",
                value=viewer.branch or "",
                disabled=True,
                help="Filial fixa conforme o perfil do usuário.",
            )
            filtro_filial = [viewer.branch] if viewer.branch else []

        clientes_disponiveis = sorted(df["cliente"].dropna().unique())
        filtro_cliente = st.multiselect("Cliente", clientes_disponiveis)

        cidades_disponiveis = sorted(df["cidade_entrega"].dropna().unique())
        filtro_cidade = st.multiselect("Cidade", cidades_disponiveis)

        situacao = st.selectbox(
            "Situação",
            ["Todas", "Atrasadas", "Vencendo hoje", "Em dia"],
        )

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("**Período**")
        datas_validas = df["prazo_considerado"].dropna()
        filtro_periodo = None
        if not datas_validas.empty:
            data_min = datas_validas.min().date()
            data_max = datas_validas.max().date()
            filtro_periodo = st.date_input(
                "Prazo considerado entre",
                value=(data_min, data_max),
                min_value=data_min,
                max_value=data_max,
                help="Filtra pela data de prazo considerada.",
            )

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("**Simulador de prazo**")
        tolerancia = st.slider(
            "Tolerância extra (dias)",
            min_value=0,
            max_value=15,
            value=0,
            help="Simula o impacto de dias extras de prazo.",
        )

        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("Limpar seleção dos gráficos", use_container_width=True):
            for chave in ["grafico_barras", "grafico_situacao"]:
                st.session_state.pop(chave, None)
            st.rerun()

    return SidebarFilters(
        busca=busca or "",
        filtro_filial=list(filtro_filial),
        filtro_cliente=list(filtro_cliente),
        filtro_cidade=list(filtro_cidade),
        situacao=situacao,
        filtro_periodo=filtro_periodo if isinstance(filtro_periodo, tuple) else None,
        tolerancia=int(tolerancia),
    )
