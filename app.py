"""
app.py
-------
Portal BI de Entregas - TMB Logistica.

Login por filial (ve so os proprios dados) ou admin (ve tudo), com
indicadores gerais, grafico por filial e detalhamento (drill-down) de
cada entrega atrasada.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from auth import exigir_login, logout
from limpeza import processar_planilha, resumo_por_filial

CAMINHO_DADOS = "dados/entregas_relatorio.csv"

COR_PRIMARIA = "#1E3056"
COR_DESTAQUE = "#F6A532"
COR_SECUNDARIA = "#58A6CD"

st.set_page_config(
    page_title="Portal BI - TMB Logística",
    page_icon="logo_tmb.png",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
exigir_login()

perfil = st.session_state["perfil"]
filial_usuario = st.session_state["filial"]
nome_exibicao = st.session_state["nome_exibicao"]


# ---------------------------------------------------------------------------
# Carregar e tratar dados (com cache para nao reprocessar a cada clique)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600)
def carregar_dados():
    return processar_planilha(CAMINHO_DADOS)


try:
    df = carregar_dados()
except FileNotFoundError:
    st.error(
        f"Arquivo de dados não encontrado em `{CAMINHO_DADOS}`. "
        "Atualize a planilha nessa pasta do repositório."
    )
    st.stop()

# Filtra por filial se o usuario nao for admin
if perfil != "admin":
    df = df[df["filial"] == filial_usuario]

# ---------------------------------------------------------------------------
# Cabecalho
# ---------------------------------------------------------------------------
col_logo, col_titulo, col_usuario = st.columns([1, 4, 2])
with col_logo:
    st.image("logo_tmb.png", width=140)
with col_titulo:
    st.markdown(
        f"<h2 style='color:{COR_PRIMARIA};margin-bottom:0;'>Portal BI de Entregas</h2>"
        f"<p style='color:{COR_SECUNDARIA};margin-top:0;'>"
        f"{'Visão geral - todas as filiais' if perfil == 'admin' else filial_usuario}</p>",
        unsafe_allow_html=True,
    )
with col_usuario:
    st.markdown(f"**{nome_exibicao}**")
    if st.button("Sair"):
        logout()

st.divider()

# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------
with st.expander("Filtros", expanded=False):
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        filiais_disponiveis = sorted(df["filial"].dropna().unique())
        if perfil == "admin":
            filtro_filial = st.multiselect("Filial", filiais_disponiveis)
        else:
            filtro_filial = []  # usuario de filial nao filtra por filial

    with col2:
        clientes_disponiveis = sorted(df["cliente"].dropna().unique())
        filtro_cliente = st.multiselect("Cliente", clientes_disponiveis)

    with col3:
        cidades_disponiveis = sorted(df["cidade_entrega"].dropna().unique())
        filtro_cidade = st.multiselect("Cidade", cidades_disponiveis)

    with col4:
        situacao = st.selectbox("Situação", ["Todas", "Atrasadas", "Vencendo hoje", "Em dia"])

df_filtrado = df.copy()
if filtro_filial:
    df_filtrado = df_filtrado[df_filtrado["filial"].isin(filtro_filial)]
if filtro_cliente:
    df_filtrado = df_filtrado[df_filtrado["cliente"].isin(filtro_cliente)]
if filtro_cidade:
    df_filtrado = df_filtrado[df_filtrado["cidade_entrega"].isin(filtro_cidade)]
if situacao == "Atrasadas":
    df_filtrado = df_filtrado[df_filtrado["atrasado"]]
elif situacao == "Vencendo hoje":
    df_filtrado = df_filtrado[df_filtrado["vence_hoje"]]
elif situacao == "Em dia":
    df_filtrado = df_filtrado[~df_filtrado["atrasado"] & ~df_filtrado["vence_hoje"]]

# ---------------------------------------------------------------------------
# Indicadores (KPIs)
# ---------------------------------------------------------------------------
total_entregas = len(df_filtrado)
total_atrasadas = int(df_filtrado["atrasado"].sum())
total_vencendo = int(df_filtrado["vence_hoje"].sum())
valor_atrasado = df_filtrado.loc[df_filtrado["atrasado"], "valor_total"].sum()
pct_atraso = (total_atrasadas / total_entregas * 100) if total_entregas else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total de entregas", f"{total_entregas}")
k2.metric("Entregas atrasadas", f"{total_atrasadas}", delta=f"{pct_atraso:.1f}% do total", delta_color="inverse")
k3.metric("Vencendo hoje", f"{total_vencendo}")
k4.metric("Valor em atraso", f"R$ {valor_atrasado:,.2f}".replace(",", "_").replace(".", ",").replace("_", "."))

st.markdown("")

# ---------------------------------------------------------------------------
# Grafico por filial (so faz sentido para o admin, que ve varias filiais)
# ---------------------------------------------------------------------------
if perfil == "admin":
    resumo = resumo_por_filial(df_filtrado)
    if not resumo.empty:
        fig = px.bar(
            resumo,
            x="filial",
            y="entregas_atrasadas",
            color_discrete_sequence=[COR_DESTAQUE],
            labels={"filial": "Filial", "entregas_atrasadas": "Entregas atrasadas"},
            title="Entregas atrasadas por filial",
        )
        fig.update_layout(
            plot_bgcolor="white",
            title_font_color=COR_PRIMARIA,
            font_color=COR_PRIMARIA,
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Lista de entregas com detalhamento (drill-down)
# ---------------------------------------------------------------------------
st.subheader("Entregas")

if df_filtrado.empty:
    st.info("Nenhuma entrega encontrada para os filtros selecionados.")
else:
    df_ordenado = df_filtrado.sort_values("dias_atraso", ascending=False)

    for _, entrega in df_ordenado.iterrows():
        if entrega["atrasado"]:
            situacao_label = f"🔴 Atrasada há {int(entrega['dias_atraso'])} dia(s)"
        elif entrega["vence_hoje"]:
            situacao_label = "🟡 Vence hoje"
        else:
            situacao_label = "🟢 Em dia"

        titulo_linha = (
            f"NF {entrega['nota_fiscal']} — {entrega['cliente']} "
            f"({entrega['filial']}) — {situacao_label}"
        )

        with st.expander(titulo_linha):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write(f"**Cliente:** {entrega['cliente']}")
                st.write(f"**Cidade:** {entrega.get('cidade_entrega', '-')}")
                st.write(f"**UF:** {entrega.get('uf_entrega', '-')}")
            with c2:
                st.write(f"**Valor total:** R$ {entrega['valor_total']:,.2f}".replace(",", "_").replace(".", ",").replace("_", "."))
                st.write(f"**Volumes:** {entrega.get('qtde_volumes', '-')}")
                st.write(f"**Status:** {entrega['status']}")
            with c3:
                st.write(f"**Prazo atual:** {entrega['dt_prazo_atual']:%d/%m/%Y}" if pd.notna(entrega['dt_prazo_atual']) else "**Prazo atual:** -")
                st.write(f"**Agendamento:** {entrega['dt_agendamento']:%d/%m/%Y}" if pd.notna(entrega['dt_agendamento']) else "**Agendamento:** -")
                st.write(f"**Prazo considerado:** {entrega['prazo_considerado']:%d/%m/%Y}" if pd.notna(entrega['prazo_considerado']) else "-")

            if pd.notna(entrega.get("motivo_atraso")):
                st.warning(f"Motivo do atraso: {entrega['motivo_atraso']}")
