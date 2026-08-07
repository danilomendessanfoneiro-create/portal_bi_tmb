"""Aba Progressão — evolução de status entre uploads manuais."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.controllers.navigation import render_bi_filters_panel, resolve_progressao_window
from app.services.access_scope_service import AccessScopeService, ViewerContext
from app.services.progress_snapshot_service import ProgressSnapshotService
from app.utils.style import kpi_card

TMB_NAVY = "#1E3056"
TMB_ORANGE = "#E67E22"


def render_progressao(
    *,
    viewer: ViewerContext,
    scope: AccessScopeService,
    hoje: date,
) -> None:
    svc = ProgressSnapshotService()
    date_from, date_to = resolve_progressao_window(hoje)
    if date_from > date_to:
        st.warning("Data inicial maior que a final.")
        return

    forced = scope.resolve_branch_filter(viewer, None)
    opts = svc.filter_options(
        date_from=date_from,
        date_to=date_to,
        filiais=forced or None,
    )

    filtros = render_bi_filters_panel(
        viewer=viewer,
        mode="progressao",
        filiais=opts["filiais"],
        clientes=opts["clientes"],
        cidades=opts["cidades"],
        status_opts=opts.get("statuses") or [],
        hoje=hoje,
    )

    date_from = filtros.date_from or date_from
    date_to = filtros.date_to or date_to
    branch_filter = scope.resolve_branch_filter(viewer, filtros.filtro_filial)

    runs, series = svc.status_series(
        date_from=date_from,
        date_to=date_to,
        filiais=branch_filter or None,
        clientes=filtros.filtro_cliente or None,
        cidades=filtros.filtro_cidade or None,
        statuses=filtros.filtro_status or None,
        busca=filtros.busca or None,
    )

    entregues = svc.count_pedidos_entregues(
        date_from=date_from,
        date_to=date_to,
        filiais=branch_filter or None,
        clientes=filtros.filtro_cliente or None,
        cidades=filtros.filtro_cidade or None,
        statuses=filtros.filtro_status or None,
        busca=filtros.busca or None,
    )
    consolidados = svc.count_pedidos_consolidados(
        date_from=date_from,
        date_to=date_to,
        filiais=branch_filter or None,
        clientes=filtros.filtro_cliente or None,
        cidades=filtros.filtro_cidade or None,
        statuses=filtros.filtro_status or None,
        busca=filtros.busca or None,
    )

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(
            kpi_card("package", TMB_NAVY, "Uploads no período", f"{len(runs)}"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            kpi_card("alert", "1E8A5F", "Pedidos Entregues", f"{entregues}"),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            kpi_card("package", TMB_ORANGE, "Pedidos consolidados", f"{consolidados}"),
            unsafe_allow_html=True,
        )

    if len(runs) < 2:
        st.info(
            "É necessário ao menos **2 uploads manuais** no período para ver evolução e Pedidos Entregues."
        )
        if len(runs) == 1 and not series.empty:
            st.caption("Distribuição do único upload disponível:")
        elif not runs:
            return

    if series.empty:
        st.info("Nenhum item de progressão no período/filtros.")
        return

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">Quantidade por STATUS PRAZO entre uploads</div>',
        unsafe_allow_html=True,
    )

    status_col = "status_prazo" if "status_prazo" in series.columns else "status"
    pivot = (
        series.pivot_table(
            index="label",
            columns=status_col,
            values="qty",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    # Preserve run order
    order = [pd.Timestamp(r["captured_at"]).strftime("%d/%m %H:%M") for r in runs]
    pivot["label"] = pd.Categorical(pivot["label"], categories=order, ordered=True)
    pivot = pivot.sort_values("label")

    fig = go.Figure()
    palette = px.colors.qualitative.Set2
    status_cols = [c for c in pivot.columns if c != "label"]
    for idx, status in enumerate(status_cols):
        fig.add_trace(
            go.Bar(
                name=str(status),
                x=pivot["label"].astype(str),
                y=pivot[status],
                marker_color=palette[idx % len(palette)],
            )
        )
    fig.update_layout(
        barmode="group",
        height=420,
        margin=dict(l=20, r=20, t=30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TMB_NAVY),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
