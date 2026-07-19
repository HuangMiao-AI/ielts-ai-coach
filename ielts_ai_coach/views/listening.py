"""Listening practice page."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User


def render_listening_page(user: User) -> None:
    """Render an honest listening demo boundary."""

    del user
    st.title("听力练习")
    st.info("当前为界面演示入口，暂未提供音频题库或听力自动评分。")
