"""
app.py
-------
Portal BI de Entregas - TMB Logistica (v3).

Novidades desta versao:
- Horario "Atualizado em" e o calculo de "hoje" usam o fuso de Brasilia;
- Filtro de periodo (por prazo considerado) na barra lateral;
- Os graficos funcionam como filtro: clicar numa barra ou fatia filtra a
  tabela de entregas abaixo;
- O detalhamento de cada entrega (drill-through) ganhou mais campos:
  data de cadastro, motorista, remetente e peso.
"""

import os
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import exigir_login, logout
from limpeza import processar_planilha
from estilo import aplicar_estilo, kpi_card

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_DADOS = os.path.join(BASE_DIR, "dados", "entregas_relatorio.csv")
CAMINHO_USUARIOS = os.path.join(BASE_DIR, "usuarios.csv")
CAMINHO_LOGO = os.path.join(BASE_DIR, "logo_tmb.png")

FUSO_BR = ZoneInfo("America/Sao_Paulo")


def agora_br() -> pd.Timestamp:
    """Data/hora atual no fuso de Brasilia (com fuso horario)."""
    return pd.Timestamp.now(tz=FUSO_BR)


st.set_page_config(page_title="Portal BI - TMB Logística", page_icon=CAMINHO_LOGO, layout="wide")

exigir_login(CAMINHO_USUARIOS)
aplicar_estilo()

perfil = st.session_state["perfil"]
filial_usuario = st.session_state["filial"]
nome_exibicao = st.session_state["nome_exibicao"]

# "Hoje" para todos os calculos de atraso, sempre baseado no fuso de Brasilia
# (sem fuso, so a data - para comparar com as colunas de data da planilha,
# que nao tem fuso).
hoje = pd.Timestamp(agora_br().date())


@st.cache_data(ttl=600)
def carregar_dados(data_ref):
    return processar_planilha(CAMINHO_DADOS, data_referencia=data_ref)


try:
    df = carregar_dados(hoje.date())
except FileNotFoundError:
    st.error(f"Arquivo de dados não encontrado em `{CAMINHO_DADOS}`. Atualize a planilha nessa pasta do repositório.")
    st.stop()

if perfil != "admin":
    df = df[df["filial"] == filial_usuario]

# ---------------------------------------------------------------------------
# Sidebar: marca, filtros, periodo e simulador
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image(CAMINHO_LOGO, use_container_width=True)
    st.markdown(
        f"<p style='color:#AFC0DA;font-size:0.8rem;margin-top:0.6rem;'>Olá, <b style='color:white;'>{nome_exibicao}</b></p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown("**Filtros**")
    busca = st.text_input("Buscar por NF ou cliente", placeholder="Ex: 509656 ou Stella Doro")

    if perfil == "admin":
        filiais_disponiveis = sorted(df["filial"].dropna().unique())
        filtro_filial = st.multiselect("Filial", filiais_disponiveis)
    else:
        filtro_filial = []

    clientes_disponiveis = sorted(df["cliente"].dropna().unique())
    filtro_cliente = st.multiselect("Cliente", clientes_disponiveis)

    cidades_disponiveis = sorted(df["cidade_entrega"].dropna().unique())
    filtro_cidade = st.multiselect("Cidade", cidades_disponiveis)

    situacao = st.selectbox("Situação", ["Todas", "Em aberto", "Vencendo hoje", "Em dia"])

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
            help="Filtra pela data de prazo considerada (o maior valor entre Dt. Prazo Atual e Dt. Agendamento).",
        )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("**Simulador de prazo**")
    tolerancia = st.slider(
        "Tolerância extra (dias)", min_value=0, max_value=15, value=0,
        help="Simula o impacto de dar alguns dias a mais de prazo antes de considerar uma entrega atrasada.",
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("Limpar seleção dos gráficos", use_container_width=True):
        for chave in ["grafico_barras", "grafico_situacao"]:
            st.session_state.pop(chave, None)
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("Sair", use_container_width=True):
        logout()

# ---------------------------------------------------------------------------
# Simulador: recalcula atraso com a tolerancia escolhida (sempre com o "hoje"
# de Brasilia calculado acima)
# ---------------------------------------------------------------------------
limite = hoje - pd.Timedelta(days=tolerancia)
elegivel = ~df["cancelada"] & ~df["entregue"] & df["prazo_considerado"].notna()
df["atrasado"] = elegivel & (df["prazo_considerado"] < limite)
df["dias_atraso"] = np.where(df["atrasado"], (hoje - df["prazo_considerado"]).dt.days, 0)

# ---------------------------------------------------------------------------
# Aplica filtros da barra lateral
# ---------------------------------------------------------------------------
df_filtrado = df.copy()
if filtro_filial:
    df_filtrado = df_filtrado[df_filtrado["filial"].isin(filtro_filial)]
if filtro_cliente:
    df_filtrado = df_filtrado[df_filtrado["cliente"].isin(filtro_cliente)]
if filtro_cidade:
    df_filtrado = df_filtrado[df_filtrado["cidade_entrega"].isin(filtro_cidade)]
if situacao == "Em aberto":
    df_filtrado = df_filtrado[df_filtrado["atrasado"]]
elif situacao == "Vencendo hoje":
    df_filtrado = df_filtrado[df_filtrado["vence_hoje"]]
elif situacao == "Em dia":
    df_filtrado = df_filtrado[~df_filtrado["atrasado"] & ~df_filtrado["vence_hoje"]]
if busca:
    b = busca.strip().lower()
    df_filtrado = df_filtrado[
        df_filtrado["nota_fiscal"].astype(str).str.lower().str.contains(b)
        | df_filtrado["cliente"].astype(str).str.lower().str.contains(b)
    ]
if isinstance(filtro_periodo, tuple) and len(filtro_periodo) == 2:
    ini, fim = filtro_periodo
    df_filtrado = df_filtrado[
        df_filtrado["prazo_considerado"].dt.date.between(ini, fim)
        | df_filtrado["prazo_considerado"].isna()
    ]

# ---------------------------------------------------------------------------
# Cabecalho
# ---------------------------------------------------------------------------
col_titulo, col_data = st.columns([3, 1])
with col_titulo:
    st.markdown('<p class="brand-title">Portal BI de Entregas</p>', unsafe_allow_html=True)
    subtitulo = "Visão geral · todas as filiais" if perfil == "admin" else filial_usuario
    st.markdown(f'<p class="brand-sub">{subtitulo}</p>', unsafe_allow_html=True)
with col_data:
    st.markdown(
        f"<div style='text-align:right;color:#64748B;font-size:0.85rem;padding-top:0.6rem;'>"
        f"Atualizado em (horário de Brasília)<br><b style='color:#1E3056;'>{agora_br():%d/%m/%Y às %H:%M}</b></div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
total_entregas = len(df_filtrado)
total_atrasadas = int(df_filtrado["atrasado"].sum())
total_vencendo = int(df_filtrado["vence_hoje"].sum())
valor_atrasado = df_filtrado.loc[df_filtrado["atrasado"], "valor_total"].sum()
pct_atraso = (total_atrasadas / total_entregas * 100) if total_entregas else 0


def fmt_moeda(v):
    if pd.isna(v):
        return "-"
    return f"R$ {v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(kpi_card("package", "1E3056", "Total de entregas", f"{total_entregas}"), unsafe_allow_html=True)
with k2:
    tipo = "tag-danger" if pct_atraso > 30 else ("tag-warning" if pct_atraso > 10 else "tag-success")
    st.markdown(kpi_card("alert", "C0392B", "Entregas em Aberto", f"{total_atrasadas}", f"{pct_atraso:.1f}% do total", tipo), unsafe_allow_html=True)
with k3:
    st.markdown(kpi_card("clock", "B9770E", "Vencendo hoje", f"{total_vencendo}"), unsafe_allow_html=True)
with k4:
    st.markdown(kpi_card("dollar", "1E8A5F", "Valor em Aberto", fmt_moeda(valor_atrasado)), unsafe_allow_html=True)

st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Graficos (funcionam tambem como filtro da tabela abaixo)
# ---------------------------------------------------------------------------
coluna_grafico1 = "filial" if perfil == "admin" else "cliente"

col_esq, col_dir = st.columns([1.3, 1])

with col_esq:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    if perfil == "admin":
        st.markdown('<div class="section-title">Entregas em aberto por filial</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Clique numa barra para filtrar a tabela abaixo só por ela</div>', unsafe_allow_html=True)
        agrupado = (
            df_filtrado[df_filtrado["atrasado"]]
            .groupby("filial").size().reset_index(name="atrasadas")
            .sort_values("atrasadas", ascending=True)
        )
    else:
        st.markdown('<div class="section-title">Entregas em aberto por cliente</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Clique numa barra para filtrar a tabela abaixo só por ela</div>', unsafe_allow_html=True)
        agrupado = (
            df_filtrado[df_filtrado["atrasado"]]
            .groupby("cliente").size().reset_index(name="atrasadas")
            .sort_values("atrasadas", ascending=True)
            .tail(8)
        )
        agrupado = agrupado.rename(columns={"cliente": "filial"})

    filial_clicada = None
    if agrupado.empty:
        st.info("Nenhuma entrega em aberto para os filtros selecionados.")
    else:
        fig = go.Figure(go.Bar(
            x=agrupado["atrasadas"], y=agrupado["filial"], orientation="h",
            marker=dict(
                color=agrupado["atrasadas"], colorscale=[[0, "#F8CB84"], [1, "#C0392B"]],
                line=dict(width=0),
            ),
            text=agrupado["atrasadas"], textposition="outside",
            hovertemplate="<b>%{y}</b><br>%{x} entregas atrasadas<extra></extra>",
        ))
        fig.update_layout(
            margin=dict(l=0, r=20, t=10, b=10), height=320,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#1E3056", size=12),
            xaxis=dict(showgrid=True, gridcolor="#EEF1F6", zeroline=False),
            yaxis=dict(showgrid=False),
            showlegend=False, clickmode="event+select",
        )
        evento_bar = st.plotly_chart(
            fig, use_container_width=True, config={"displayModeBar": False},
            on_select="rerun", selection_mode="points", key="grafico_barras",
        )
        pontos = evento_bar.selection.points if evento_bar and evento_bar.selection else []
        if pontos:
            filial_clicada = pontos[0].get("y")
    st.markdown('</div>', unsafe_allow_html=True)

with col_dir:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Distribuição por situação</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Clique numa fatia para filtrar a tabela abaixo</div>', unsafe_allow_html=True)

    n_em_dia = total_entregas - total_atrasadas - total_vencendo
    dados_pie = pd.DataFrame({
        "situacao": ["Em aberto", "Vencendo hoje", "Em dia"],
        "valor": [total_atrasadas, total_vencendo, max(n_em_dia, 0)],
    })
    cores_pie = {"Em aberto": "#C0392B", "Vencendo hoje": "#F6A532", "Em dia": "#1E8A5F"}

    situacao_clicada = None
    if total_entregas == 0:
        st.info("Sem dados para os filtros selecionados.")
    else:
        fig2 = go.Figure(go.Pie(
            labels=dados_pie["situacao"], values=dados_pie["valor"], hole=0.65,
            marker=dict(colors=[cores_pie[s] for s in dados_pie["situacao"]]),
            textinfo="percent", textfont=dict(size=12, family="Inter, sans-serif"),
            hovertemplate="<b>%{label}</b><br>%{value} entregas<extra></extra>",
        ))
        fig2.update_layout(
            margin=dict(l=0, r=0, t=10, b=0), height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#1E3056", size=12),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, x=0.5, xanchor="center"),
            annotations=[dict(text=f"<b>{total_entregas}</b><br><span style='font-size:11px;color:#64748B'>entregas</span>",
                               x=0.5, y=0.5, showarrow=False, font=dict(size=20, color="#1E3056", family="Manrope, sans-serif"))],
            clickmode="event+select",
        )
        evento_pie = st.plotly_chart(
            fig2, use_container_width=True, config={"displayModeBar": False},
            on_select="rerun", selection_mode="points", key="grafico_situacao",
        )
        pontos_pie = evento_pie.selection.points if evento_pie and evento_pie.selection else []
        if pontos_pie:
            situacao_clicada = pontos_pie[0].get("label")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Aplica o filtro vindo dos graficos (cross-filter) sobre a base da tabela
# ---------------------------------------------------------------------------
df_tabela_base = df_filtrado.copy()
filtros_grafico_ativos = []

if filial_clicada:
    df_tabela_base = df_tabela_base[df_tabela_base[coluna_grafico1] == filial_clicada]
    rotulo = "Filial" if perfil == "admin" else "Cliente"
    filtros_grafico_ativos.append(f"{rotulo}: <b>{filial_clicada}</b>")

if situacao_clicada:
    if situacao_clicada == "Em aberto":
        df_tabela_base = df_tabela_base[df_tabela_base["atrasado"]]
    elif situacao_clicada == "Vencendo hoje":
        df_tabela_base = df_tabela_base[df_tabela_base["vence_hoje"]]
    elif situacao_clicada == "Em dia":
        df_tabela_base = df_tabela_base[~df_tabela_base["atrasado"] & ~df_tabela_base["vence_hoje"]]
    filtros_grafico_ativos.append(f"Situação: <b>{situacao_clicada}</b>")

if filtros_grafico_ativos:
    st.markdown(
        f"<div style='background:#FFF4E0;border:1px solid #F6D9A0;border-radius:10px;"
        f"padding:0.55rem 0.9rem;font-size:0.85rem;color:#8A5A00;margin-bottom:0.8rem;'>"
        f"🔎 Filtro aplicado pelo gráfico — {' · '.join(filtros_grafico_ativos)}. "
        f"Use \"Limpar seleção dos gráficos\", na barra lateral, para remover.</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Tabela de dados + detalhamento (drill-through)
# ---------------------------------------------------------------------------
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Entregas</div>', unsafe_allow_html=True)
st.markdown(f'<div class="section-sub">{len(df_tabela_base)} entrega(s) — clique numa linha para ver o detalhamento completo</div>', unsafe_allow_html=True)

if df_tabela_base.empty:
    st.info("Nenhuma entrega encontrada para os filtros selecionados.")
else:
    def situacao_label(row):
        if row["atrasado"]:
            return f"🔴 Em aberto ({int(row['dias_atraso'])}d)"
        if row["vence_hoje"]:
            return "🟡 Vence hoje"
        return "🟢 Em dia"

    df_tabela = df_tabela_base.sort_values("dias_atraso", ascending=False).copy()
    df_tabela["Situação"] = df_tabela.apply(situacao_label, axis=1)

    colunas_exibir = ["nota_fiscal", "cliente"]
    if perfil == "admin":
        colunas_exibir.append("filial")
    colunas_exibir += ["cidade_entrega", "dt_agendamento", "Situação"]

    evento = st.dataframe(
        df_tabela[colunas_exibir],
        use_container_width=True,
        hide_index=True,
        height=380,
        column_config={
            "nota_fiscal": st.column_config.TextColumn("Nota Fiscal"),
            "cliente": st.column_config.TextColumn("Cliente"),
            "filial": st.column_config.TextColumn("Filial"),
            "cidade_entrega": st.column_config.TextColumn("Cidade"),
            "dt_agendamento": st.column_config.DateColumn("Agendamento", format="DD/MM/YYYY"),
            "Situação": st.column_config.TextColumn("Situação"),
        },
        on_select="rerun",
        selection_mode="single-row",
    )

    linhas_selecionadas = evento.selection.rows if evento and evento.selection else []
    if linhas_selecionadas:
        entrega = df_tabela.iloc[linhas_selecionadas[0]]
        peso = entrega.get("peso_taxado")
        if pd.isna(peso):
            peso = entrega.get("peso_informado")

        st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
        st.markdown(f"**Detalhamento — NF {entrega['nota_fiscal']}**")

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.caption("Cliente (destinatário)")
            st.write(entrega["cliente"])
            st.caption("Cidade / UF de entrega")
            st.write(f"{entrega.get('cidade_entrega', '-')} / {entrega.get('uf_entrega', '-')}")
        with d2:
            st.caption("Remetente")
            st.write(entrega.get("remetente") if pd.notna(entrega.get("remetente")) else "-")
            st.caption("Cidade / UF de origem")
            st.write(f"{entrega.get('cidade_remetente', '-')} / {entrega.get('uf_remetente', '-')}")
        with d3:
            st.caption("Valor total")
            st.write(fmt_moeda(entrega["valor_total"]))
            st.caption("Peso (kg)")
            st.write(f"{peso:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".") if pd.notna(peso) else "-")
        with d4:
            st.caption("Volumes")
            st.write(entrega.get("qtde_volumes", "-"))
            st.caption("Motorista")
            st.write(entrega.get("motorista") if pd.notna(entrega.get("motorista")) else "Não informado")

        st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)
        e1, e2, e3, e4, e5 = st.columns(5)
        with e1:
            st.caption("Data de entrada no sistema")
            st.write(f"{entrega['dt_cadastro']:%d/%m/%Y %H:%M}" if pd.notna(entrega.get("dt_cadastro")) else "-")
        with e2:
            st.caption("Data de entrega")
            st.write(f"{entrega['dt_entrega']:%d/%m/%Y}" if pd.notna(entrega.get("dt_entrega")) else "-")
        with e3:
            st.caption("Prazo atual")
            st.write(f"{entrega['dt_prazo_atual']:%d/%m/%Y}" if pd.notna(entrega["dt_prazo_atual"]) else "-")
        with e4:
            st.caption("Agendamento")
            st.write(f"{entrega['dt_agendamento']:%d/%m/%Y}" if pd.notna(entrega["dt_agendamento"]) else "-")
        with e5:
            st.caption("Status no sistema")
            st.write(entrega["status"])

        if pd.notna(entrega.get("motivo_atraso")):
            st.warning(f"Motivo do atraso: {entrega['motivo_atraso']}")

st.markdown('</div>', unsafe_allow_html=True)
