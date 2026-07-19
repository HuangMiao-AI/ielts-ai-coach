"""Streamlit entry point for IELTS AI Coach V1."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.auth import AuthenticationRequiredError, require_login
from ielts_ai_coach.config import (
    APP_SUBTITLE,
    APP_TITLE,
    ensure_supported_python,
)
from ielts_ai_coach.database.backup import backup_database_if_due
from ielts_ai_coach.database.connection import initialize_database
from ielts_ai_coach.ui.styles import apply_styles
from ielts_ai_coach.views.login import render_auth_page
from ielts_ai_coach.views.navigation import render_authenticated_app


ensure_supported_python()
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)


def initialize_application() -> None:
    """Initialize database infrastructure required by every page."""

    initialize_database()
    backup_database_if_due()


def main() -> None:
    """Route the current Streamlit session to its appropriate page."""

    initialize_application()
    apply_styles()

    try:
        current_user = require_login()
    except AuthenticationRequiredError:
        render_auth_page()
    else:
        render_authenticated_app(current_user)

    st.caption(f"{APP_TITLE} · {APP_SUBTITLE}")


if __name__ == "__main__":
    main()
