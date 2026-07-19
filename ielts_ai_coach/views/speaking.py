"""Speaking practice page."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User


def render_speaking_page(user: User) -> None:
    """Render an honest speaking demo boundary."""

    del user
    st.title("口语练习")
    st.info("本地录音练习将在后续阶段接入；当前不提供口语自动评分。")
