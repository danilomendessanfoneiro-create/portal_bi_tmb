"""Seção Histórico do BI — evolução diária de atrasos (snapshots)."""

from __future__ import annotations

from datetime import date

import plotly.graph_objects as go
import streamlit as st

from app.controllers.navigation import render_bi_filters_panel, resolve_historico_window
from app.services.access_scope_service import ViewerContext, AccessScopeService
from app.services.bi_snapshot_service import BiSnapshotService
from app.utils.style import kpi_card


def render_historico(
    *,
    viewer: ViewerContext,
    scope: AccessScopeService,
    hoje: date,
) -> None:
    svc = BiSnapshotService()
    date_from, date_to = resolve_historico_window(hoje)
    if date_from > date_to:
        st.warning("Data inicial maior que a final.")
        return

    forced = scope.resolve_branch_filter(viewer, None)
    filter_opts = svc.filter_options(
        date_from=date_from,
        date_to=date_to,
        filiais=forced or None,
    )

    filtros = render_bi_filters_panel(
        viewer=viewer,
        mode="historico",
        filiais=filter_opts["filiais"],
        clientes=filter_opts["clientes"],
        cidades=filter_opts["cidades"],
        hoje=hoje,
    )

    if filtros.date_from and filtros.date_to and filtros.date_from > filtros.date_to:
        st.warning("Data inicial maior que a final.")
        return

    date_from = filtros.date_from or date_from
    date_to = filtros.date_to or date_to

    branch_filter = scope.resolve_branch_filter(viewer, filtros.filtro_filial)
    series = svc.aggregate_series(
        date_from=date_from,
        date_to=date_to,
        filiais=branch_filter or None,
        clientes=filtros.filtro_cliente or None,
        cidades=filtros.filtro_cidade or None,
        busca=filtros.busca or None,
    )

    if series.empty:
        st.info("Nenhum snapshot no período. Rode o relatório diário ou o seed de demo.")
        return

    total = int(series["overdue_count"].sum())
    media = float(series["overdue_count"].mean()) if len(series) else 0.0
    ultimo = int(series.iloc[-1]["overdue_count"])
    delta = None
    if len(series) >= 2:
        delta = ultimo - int(series.iloc[-2]["overdue_count"])

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(
            kpi_card("package", "1E3056", "Total no período", f"{total}"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            kpi_card("clock", "B9770E", "Média diária", f"{media:.1f}"),
            unsafe_allow_html=True,
        )
    with k3:
        delta_txt = f"{delta:+d} vs dia anterior" if delta is not None else "fotografias diárias"
        st.markdown(
            kpi_card("alert", "C0392B", "Último dia", f"{ultimo}", delta_txt),
            unsafe_allow_html=True,
        )

    fig = go.Figure(
        data=[
            go.Bar(
                x=[d.isoformat() if hasattr(d, "isoformat") else str(d) for d in series["business_date"]],
                y=series["overdue_count"],
                marker_color="#E0042B",
            )
        ]
    )
    fig.update_layout(
        title="Evolução de entregas em atraso",
        xaxis_title="Dia",
        yaxis_title="Qtde em atraso",
        margin=dict(l=20, r=20, t=50, b=40),
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Dados agregados"):
        st.dataframe(
            series.rename(columns={"business_date": "Dia", "overdue_count": "Atrasos"}),
            use_container_width=True,
            hide_index=True,
        )
