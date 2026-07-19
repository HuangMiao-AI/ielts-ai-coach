"""Visual styling entry point for the Streamlit application."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.ui.design_system import build_app_css


APP_CSS = build_app_css()


def apply_styles() -> None:
    """Apply the shared CSS used by public and protected pages."""

    st.markdown(APP_CSS, unsafe_allow_html=True)
