"""
Portal BI de Entregas - TMB Logística
Entry point (thin router). Architecture lives under app/.
"""

from __future__ import annotations

import streamlit as st

from app.config import settings
from app.controllers.auth_controller import require_login
from app.controllers.dashboard_controller import render_dashboard
from app.utils.embed import apply_embed_chrome
from app.utils.style import aplicar_estilo

st.set_page_config(
    page_title="Portal BI - TMB Logística",
    page_icon=str(settings.logo_path) if settings.logo_path.exists() else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

require_login()
aplicar_estilo()
apply_embed_chrome()
render_dashboard()
