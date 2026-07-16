"""
estilo.py
----------
Estilo visual compartilhado do portal (cores, tipografia, cards).
Chame aplicar_estilo() uma vez, no topo de cada pagina (login e app).
"""

import base64
import os
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ICONES = os.path.join(BASE_DIR, "assets", "icons")

NAVY = "#1E3056"
NAVY_DARK = "#142240"
ORANGE = "#F6A532"
BLUE = "#58A6CD"
DANGER = "#C0392B"
SUCCESS = "#1E8A5F"
WARNING = "#B9770E"
TEXT_MUTED = "#64748B"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, p, span, div {
    font-family: 'Inter', -apple-system, sans-serif;
}
h1, h2, h3, .kpi-value, .brand-title {
    font-family: 'Manrope', sans-serif !important;
}

.stApp { background: #F5F7FA; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1E3056 0%, #142240 100%);
}
section[data-testid="stSidebar"] * { color: #E7ECF5 !important; }
section[data-testid="stSidebar"] label {
    color: #AFC0DA !important; font-weight: 700; font-size: 0.72rem;
    text-transform: uppercase; letter-spacing: 0.04em;
}
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12); }

/* ---- cards de indicador (KPI) ---- */
.kpi-card {
    background: #FFFFFF; border-radius: 16px; padding: 1.25rem 1.4rem;
    box-shadow: 0 4px 18px rgba(30,48,86,0.07); border: 1px solid #EBEFF5;
    height: 100%;
}
.kpi-icon {
    width: 40px; height: 40px; border-radius: 11px;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 0.65rem;
}
.kpi-icon img { width: 20px; height: 20px; }
.kpi-label {
    font-size: 0.74rem; color: #64748B; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.1rem;
}
.kpi-value { font-size: 1.85rem; font-weight: 800; color: #1E3056; line-height: 1.15; }
.kpi-delta {
    font-size: 0.74rem; font-weight: 700; margin-top: 0.4rem;
    display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px;
}
.kpi-delta.tag-danger { background: #FDECEA; color: #C0392B; }
.kpi-delta.tag-warning { background: #FFF4E0; color: #B9770E; }
.kpi-delta.tag-success { background: #E8F6F0; color: #1E8A5F; }
.kpi-delta.tag-neutral { background: #EEF1F6; color: #64748B; }

/* ---- cards de secao (graficos, tabela) ---- */
.section-card {
    background: #FFFFFF; border-radius: 16px; padding: 1.35rem 1.5rem 1.1rem;
    box-shadow: 0 4px 18px rgba(30,48,86,0.06); border: 1px solid #EBEFF5;
    margin-bottom: 1.1rem;
}
.section-title { font-weight: 800; font-size: 1.02rem; color: #1E3056; margin-bottom: 0.1rem; }
.section-sub { font-size: 0.8rem; color: #64748B; margin-bottom: 0.7rem; }

/* ---- badges de situacao ---- */
.badge { display:inline-block; padding: 0.22rem 0.65rem; border-radius: 999px; font-size: 0.72rem; font-weight: 700; }
.badge-atrasado { background:#FDECEA; color:#C0392B; }
.badge-hoje { background:#FFF4E0; color:#B9770E; }
.badge-ok { background:#E8F6F0; color:#1E8A5F; }

/* ---- cabecalho ---- */
.brand-title { font-size: 1.55rem; font-weight: 800; color: #1E3056; margin: 0; }
.brand-sub { font-size: 0.92rem; color: #58A6CD; font-weight: 600; margin-top: -0.15rem; }

/* ---- login ---- */
.login-card {
    background: #FFFFFF; border-radius: 20px; padding: 2.2rem 2.4rem;
    box-shadow: 0 12px 36px rgba(30,48,86,0.16); border: 1px solid #EBEFF5;
}

div[data-testid="stMetricValue"] { color: #1E3056; }
.stButton>button {
    border-radius: 10px; font-weight: 700; border: none;
    background: #1E3056; color: white;
}
.stButton>button:hover { background: #142240; color: white; }

hr.custom-divider { border: none; border-top: 1px solid #E4E9F1; margin: 1.4rem 0; }
</style>
"""


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)


def _icone_base64(nome: str, cor_hex: str) -> str:
    caminho = os.path.join(PASTA_ICONES, f"{nome}_{cor_hex}.png")
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def kpi_card(icone: str, cor_fundo: str, label: str, valor: str, delta_texto: str = None, delta_tipo: str = "neutral"):
    """Gera o HTML de um card de indicador. cor_fundo em hex sem '#', ex: '1E3056'."""
    icone_b64 = _icone_base64(icone, "FFFFFF")
    delta_html = ""
    if delta_texto:
        delta_html = f'<div class="kpi-delta tag-{delta_tipo}">{delta_texto}</div>'
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon" style="background:#{cor_fundo};">
            <img src="data:image/png;base64,{icone_b64}" />
        </div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{valor}</div>
        {delta_html}
    </div>
    """
