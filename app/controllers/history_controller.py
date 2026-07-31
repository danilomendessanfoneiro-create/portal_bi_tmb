"""Seção Histórico do BI — evolução diária + Detalhe do dia (drill-down)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.controllers.navigation import render_bi_filters_panel, resolve_historico_window
from app.services.access_scope_service import ViewerContext, AccessScopeService
from app.services.bi_snapshot_service import BiSnapshotService
from app.utils.style import kpi_card

HIST_DAY_KEY = "bi_hist_detail_day"
HIST_DRILL_KEY = "bi_hist_detail_drill"
HIST_CHART_SERIES_KEY = "grafico_historico_serie"
HIST_CHART_BREAKDOWN_KEY = "grafico_historico_breakdown"
HIST_SELECT_KEY = "bi_hist_day_select"


def _fmt_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _parse_day(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        ts = pd.Timestamp(value)
        if pd.isna(ts):
            return None
        return ts.date()
    except (TypeError, ValueError):
        return None


def _fmt_moeda(v) -> str:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "R$ 0,00"
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def _clear_day_detail() -> None:
    st.session_state.pop(HIST_DAY_KEY, None)
    st.session_state.pop(HIST_DRILL_KEY, None)
    st.session_state[HIST_SELECT_KEY] = "(nenhum)"


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

    day_labels = [_fmt_br(d) if isinstance(d, date) else str(d) for d in series["business_date"]]
    day_iso = [
        d.isoformat() if hasattr(d, "isoformat") else str(d) for d in series["business_date"]
    ]
    label_to_date = {
        _fmt_br(d) if isinstance(d, date) else str(d): (d if isinstance(d, date) else _parse_day(d))
        for d in series["business_date"]
    }

    fig = go.Figure(
        data=[
            go.Bar(
                x=day_iso,
                y=series["overdue_count"],
                marker_color="#E0042B",
                customdata=day_iso,
                hovertemplate="<b>%{x}</b><br>%{y} em atraso<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="Evolução de entregas em atraso — clique num dia para detalhar",
        xaxis_title="Dia",
        yaxis_title="Qtde em atraso",
        margin=dict(l=20, r=20, t=50, b=40),
        height=420,
        clickmode="event+select",
    )
    evento = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key=HIST_CHART_SERIES_KEY,
    )
    pontos = evento.selection.points if evento and evento.selection else []
    if pontos:
        raw = pontos[0].get("x") or pontos[0].get("customdata")
        idx = pontos[0].get("point_number", pontos[0].get("point_index"))
        picked = _parse_day(raw)
        if picked is None and idx is not None:
            try:
                picked = _parse_day(series.iloc[int(idx)]["business_date"])
            except (TypeError, ValueError, IndexError):
                picked = None
        if picked is not None and picked != st.session_state.get(HIST_DAY_KEY):
            st.session_state[HIST_DAY_KEY] = picked
            st.session_state.pop(HIST_DRILL_KEY, None)
            st.session_state[HIST_SELECT_KEY] = _fmt_br(picked)
            # sem st.rerun(): mantém a aba Histórico e renderiza o detalhe neste run

    opts = ["(nenhum)"] + day_labels
    current_day = st.session_state.get(HIST_DAY_KEY)
    if HIST_SELECT_KEY not in st.session_state:
        st.session_state[HIST_SELECT_KEY] = (
            _fmt_br(current_day) if isinstance(current_day, date) else "(nenhum)"
        )
    if st.session_state[HIST_SELECT_KEY] not in opts:
        st.session_state[HIST_SELECT_KEY] = "(nenhum)"

    c_sel, c_clr = st.columns([3, 1])
    with c_sel:
        chosen = st.selectbox(
            "Dia para detalhar",
            opts,
            key=HIST_SELECT_KEY,
            help="Fallback se o clique no gráfico não capturar a seleção.",
        )
    with c_clr:
        st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
        st.button(
            "Limpar detalhe do dia",
            width="content",
            key="bi_hist_clear_day",
            on_click=_clear_day_detail,
        )

    if chosen and chosen != "(nenhum)":
        selected = label_to_date.get(chosen)
        if selected is None:
            st.warning("Dia inválido para o período filtrado.")
        elif selected != st.session_state.get(HIST_DAY_KEY):
            st.session_state[HIST_DAY_KEY] = selected
            st.session_state.pop(HIST_DRILL_KEY, None)
    elif chosen == "(nenhum)" and st.session_state.get(HIST_DAY_KEY) is not None:
        # selectbox cleared without button
        st.session_state.pop(HIST_DAY_KEY, None)
        st.session_state.pop(HIST_DRILL_KEY, None)

    with st.expander("Dados agregados"):
        st.dataframe(
            series.rename(columns={"business_date": "Dia", "overdue_count": "Atrasos"}),
            use_container_width=True,
            hide_index=True,
        )

    detail_day = st.session_state.get(HIST_DAY_KEY)
    if detail_day is None:
        return

    detail_day = _parse_day(detail_day)
    if detail_day is None:
        st.warning("Não foi possível interpretar a data selecionada.")
        return

    series_dates = {_parse_day(d) for d in series["business_date"]}
    if detail_day not in series_dates:
        st.info(
            f"Sem snapshot/linhas para {_fmt_br(detail_day)} no período e filtros atuais. "
            "Escolha outro dia ou limpe o detalhe."
        )
        return

    _render_detalhe_do_dia(
        svc=svc,
        viewer=viewer,
        business_date=detail_day,
        branch_filter=branch_filter,
        clientes=filtros.filtro_cliente or None,
        cidades=filtros.filtro_cidade or None,
        busca=filtros.busca or None,
    )


def _render_detalhe_do_dia(
    *,
    svc: BiSnapshotService,
    viewer: ViewerContext,
    business_date: date,
    branch_filter: Optional[list[str]],
    clientes: Optional[list[str]],
    cidades: Optional[list[str]],
    busca: Optional[str],
) -> None:
    st.markdown("---")
    st.markdown(f"### Detalhe do dia {_fmt_br(business_date)}")
    st.caption(
        "Fotografia histórica das entregas em atraso (snapshot). "
        "Não reconstrói “vence hoje” / “em dia”."
    )

    df = svc.list_overdue_for_day(
        business_date=business_date,
        filiais=branch_filter or None,
        clientes=clientes,
        cidades=cidades,
        busca=busca,
    )

    dim_col = "filial" if viewer.is_admin else "cliente"
    drill = st.session_state.get(HIST_DRILL_KEY)
    if drill and dim_col in df.columns and not df.empty:
        valid = set(df[dim_col].dropna().astype(str).unique())
        if str(drill) not in valid:
            st.session_state.pop(HIST_DRILL_KEY, None)
            drill = None

    df_view = df.copy()
    if drill and dim_col in df_view.columns:
        df_view = df_view[df_view[dim_col].astype(str) == str(drill)]

    if df.empty:
        st.info("Nenhuma entrega em atraso neste dia para os filtros selecionados.")
        return

    n = len(df_view)
    valor = float(df_view["valor_total"].fillna(0).sum()) if "valor_total" in df_view.columns else 0.0
    media_dias = (
        float(df_view["dias_atraso"].mean()) if n and "dias_atraso" in df_view.columns else 0.0
    )

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(
            kpi_card("alert", "C0392B", "Em atraso", f"{n}"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            kpi_card("dollar", "1E8A5F", "Valor em atraso", _fmt_moeda(valor)),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            kpi_card("clock", "B9770E", "Média dias atraso", f"{media_dias:.1f}"),
            unsafe_allow_html=True,
        )

    filtros_ativos = []
    if drill:
        rotulo = "Filial" if dim_col == "filial" else "Cliente"
        filtros_ativos.append(f"{rotulo}: <b>{drill}</b>")
    if filtros_ativos:
        c_info, c_btn = st.columns([4, 1])
        with c_info:
            st.markdown(
                "Filtro do gráfico: " + " · ".join(filtros_ativos),
                unsafe_allow_html=True,
            )
        with c_btn:
            if st.button("Limpar drill", width="content", key="bi_hist_clear_drill"):
                st.session_state.pop(HIST_DRILL_KEY, None)
                st.rerun()

    # Breakdown usa base do dia (sem drill) para permitir re-seleção
    title = (
        "Em atraso por filial"
        if viewer.is_admin
        else "Em atraso por cliente"
    )
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">Clique numa barra para filtrar a tabela</div>',
        unsafe_allow_html=True,
    )

    if dim_col not in df.columns or df[dim_col].dropna().empty:
        st.info("Sem dimensão para o breakdown.")
    else:
        agrupado = (
            df.groupby(dim_col).size().reset_index(name="atrasadas").sort_values("atrasadas")
        )
        if not viewer.is_admin:
            agrupado = agrupado.tail(12)
        fig_b = go.Figure(
            go.Bar(
                x=agrupado["atrasadas"],
                y=agrupado[dim_col].astype(str),
                orientation="h",
                marker=dict(
                    color=agrupado["atrasadas"],
                    colorscale=[[0, "#F8CB84"], [1, "#C0392B"]],
                    line=dict(width=0),
                ),
                text=agrupado["atrasadas"],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>%{x} em atraso<extra></extra>",
            )
        )
        fig_b.update_layout(
            margin=dict(l=0, r=20, t=10, b=10),
            height=min(420, 40 + 28 * len(agrupado)),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            clickmode="event+select",
            xaxis=dict(showgrid=True, gridcolor="#EEF1F6", zeroline=False),
            yaxis=dict(showgrid=False),
        )
        ev_b = st.plotly_chart(
            fig_b,
            use_container_width=True,
            config={"displayModeBar": False},
            on_select="rerun",
            selection_mode="points",
            key=HIST_CHART_BREAKDOWN_KEY,
        )
        pts = ev_b.selection.points if ev_b and ev_b.selection else []
        if pts:
            nova = pts[0].get("y")
            if nova and str(nova) != str(st.session_state.get(HIST_DRILL_KEY)):
                st.session_state[HIST_DRILL_KEY] = str(nova)
                st.rerun()

    st.markdown('<div class="section-title">Registros do dia</div>', unsafe_allow_html=True)
    if df_view.empty:
        st.info("Nenhum registro para o drill/filtros atuais neste dia.")
        return

    tabela = df_view.sort_values("dias_atraso", ascending=False).copy()
    colunas = [
        c
        for c in [
            "nota_fiscal",
            "cliente",
            "filial",
            "cidade_entrega",
            "prazo_considerado",
            "dias_atraso",
            "valor_total",
            "status",
            "status_prazo",
            "motorista",
        ]
        if c in tabela.columns
    ]
    st.dataframe(
        tabela[colunas],
        use_container_width=True,
        hide_index=True,
        height=min(480, 80 + 35 * min(len(tabela), 12)),
        column_config={
            "nota_fiscal": st.column_config.TextColumn("Nota Fiscal"),
            "cliente": st.column_config.TextColumn("Cliente"),
            "filial": st.column_config.TextColumn("Filial"),
            "cidade_entrega": st.column_config.TextColumn("Cidade"),
            "prazo_considerado": st.column_config.DatetimeColumn("Prazo", format="DD/MM/YYYY"),
            "dias_atraso": st.column_config.NumberColumn("Dias atraso"),
            "valor_total": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "status": st.column_config.TextColumn("Status"),
            "status_prazo": st.column_config.TextColumn("Status prazo"),
            "motorista": st.column_config.TextColumn("Motorista"),
        },
    )
