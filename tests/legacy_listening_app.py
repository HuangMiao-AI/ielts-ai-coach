"""Test-only host for the retained legacy Listening Mini Practice renderer."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.views.listening import render_listening_page


st.session_state.setdefault("user_id", 1)
render_listening_page(
    User(
        id=1,
        username="LegacyListening",
        username_normalized="legacylistening",
        password_hash="unused-in-session-only-legacy-test",
    )
)
