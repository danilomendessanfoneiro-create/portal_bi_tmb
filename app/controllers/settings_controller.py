"""Settings placeholder (Administração > Configurações)."""

from __future__ import annotations

import streamlit as st


def render_settings() -> None:
    st.markdown('<p class="brand-title">Configurações</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="brand-sub">Administração · em breve</p>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Módulo reservado</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">A tela de configurações será implementada em uma próxima etapa. '
        "O item de menu já está disponível para navegação.</div>",
        unsafe_allow_html=True,
    )
    st.info("Nenhuma configuração disponível neste momento.")
    st.markdown("</div>", unsafe_allow_html=True)
