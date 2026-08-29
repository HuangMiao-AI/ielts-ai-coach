"""Guest-safe route registry with no user-owned database services."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

import streamlit as st

from ielts_ai_coach.auth import GuestIdentity, end_guest_session
from ielts_ai_coach.ui.navigation import run_hidden_navigation
from ielts_ai_coach.views.guest_dashboard import render_guest_dashboard
from ielts_ai_coach.views.guest_reading import render_guest_reading_page
from ielts_ai_coach.views.listening_vocabulary import render_listening_vocabulary_page
from ielts_ai_coach.views.training_arena import render_training_arena_page
from ielts_ai_coach.views.writing import render_writing_page


GUEST_ROUTE_META = {
    "home": ("首页", ":material/home:"),
    "reading": ("阅读", ":material/menu_book:"),
    "listening": ("听力", ":material/headphones:"),
    "writing": ("写作", ":material/edit_note:"),
    "arena": ("IELTS 训练场", ":material/sports_esports:"),
}


def _run_guest_page(
    renderer: Callable[[], None],
    refs: dict[str, st.Page],
) -> None:
    """Render guest notice, allowed navigation, and the selected page."""

    with st.sidebar:
        st.markdown("## IELTS AI Coach")
        st.caption("游客模式")
        for key in ("home", "arena", "reading", "listening", "writing"):
            st.page_link(refs[key], label=GUEST_ROUTE_META[key][0], icon=GUEST_ROUTE_META[key][1])
    with st.container(key="guest_status_bar"):
        notice, action = st.columns((4, 1))
        notice.markdown("**游客模式 · 登录后可保存学习记录**")
        if action.button("登录 / 注册", use_container_width=True):
            end_guest_session()
            st.rerun()
    with st.container(key="mobile_bottom_navigation"):
        columns = st.columns(5)
        for column, key in zip(columns, ("home", "arena", "reading", "listening", "writing")):
            with column:
                st.page_link(refs[key], label=GUEST_ROUTE_META[key][0], use_container_width=True)
    renderer()


def render_guest_app(guest: GuestIdentity) -> None:
    """Run only session-safe pages for a transient guest."""

    refs: dict[str, st.Page] = {}
    renderers: dict[str, Callable[[], None]] = {
        "home": partial(render_guest_dashboard, guest, refs),
        "reading": partial(render_guest_reading_page, guest),
        "listening": partial(render_listening_vocabulary_page, guest),
        "writing": partial(render_writing_page, guest, guest_mode=True),
        "arena": partial(render_training_arena_page, guest, refs),
    }
    for key, renderer in renderers.items():
        title, icon = GUEST_ROUTE_META[key]
        refs[key] = st.Page(
            partial(_run_guest_page, renderer, refs),
            title=title,
            icon=icon,
            url_path=key,
            default=key == "home",
        )
    run_hidden_navigation(list(refs.values()))
