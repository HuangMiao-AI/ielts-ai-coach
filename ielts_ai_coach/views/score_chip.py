"""Lightweight current-session Training Arena score display."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.services.training_arena import arena_session_score


def render_score_chip(participant_id: int) -> None:
    """Show only a verified score from the active browser session."""

    score = arena_session_score(st.session_state, participant_id)
    st.markdown(
        '<div class="score-chip"><span>本次积分</span>'
        f"<strong>{score}</strong></div>",
        unsafe_allow_html=True,
    )
