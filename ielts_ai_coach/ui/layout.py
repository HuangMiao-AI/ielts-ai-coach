"""Shared authenticated page chrome."""

from __future__ import annotations

from collections.abc import Mapping

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.ui.navigation import render_primary_navigation


def render_page_shell(
    user: User,
    refs: Mapping[str, st.Page],
    route_key: str,
    *,
    show_profile_warning: bool,
) -> None:
    """Render navigation, current-user context, and setup warning."""

    render_primary_navigation(refs, route_key)
    st.markdown(
        f'<div class="current-user">IELTS AI Coach · {user.username}</div>',
        unsafe_allow_html=True,
    )
    if show_profile_warning:
        st.warning("请先完善学习档案，之后即可录入成绩并生成计划。")
