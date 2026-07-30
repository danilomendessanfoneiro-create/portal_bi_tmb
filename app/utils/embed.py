"""Helpers for Streamlit embed mode (portal shell / iframe)."""

from __future__ import annotations

import streamlit as st

EMBED_CSS = """
<style>
header[data-testid="stHeader"] { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
footer { display: none !important; }
div[data-testid="stDecoration"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }
div[data-testid="collapsedControl"] { display: none !important; }
.block-container {
    padding-top: 1rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
}
</style>
"""


def is_embedded() -> bool:
    if st.session_state.get("embed_mode"):
        return True
    raw = st.query_params.get("embed")
    if raw is None:
        return False
    value = raw if isinstance(raw, str) else str(raw[0] if raw else "")
    embedded = value.lower() in {"1", "true", "yes"}
    if embedded:
        st.session_state["embed_mode"] = True
    return embedded


def apply_embed_chrome() -> None:
    if is_embedded():
        st.markdown(EMBED_CSS, unsafe_allow_html=True)
