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
@media (max-width: 1024px) {
    .block-container {
        padding-top: 0.65rem !important;
        padding-left: 0.65rem !important;
        padding-right: 0.65rem !important;
        padding-bottom: 1rem !important;
    }
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"] > div {
        min-width: 100% !important;
        flex: 1 1 100% !important;
        width: 100% !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.kpi-card) > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"]:has(.kpi-card) > div {
        min-width: calc(50% - 0.4rem) !important;
        flex: 1 1 calc(50% - 0.4rem) !important;
        width: calc(50% - 0.4rem) !important;
        max-width: calc(50% - 0.4rem) !important;
    }
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
