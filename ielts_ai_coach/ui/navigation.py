"""Responsive navigation shared by every authenticated page."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import streamlit as st


PRIMARY_NAVIGATION_KEYS = (
    "home",
    "reading",
    "listening",
    "writing",
    "speaking",
    "plan",
    "history",
    "profile",
)
PRIMARY_ROUTE_TITLES = (
    "首页",
    "阅读",
    "听力",
    "写作",
    "口语",
    "学习计划",
    "历史记录",
    "个人资料",
)
CONTEXTUAL_ROUTE_KEYS = ("arena", "scores", "today", "coach", "settings")


def _render_link(
    page: st.Page,
    *,
    label: str | None = None,
) -> None:
    """Render one accessible route link."""

    st.page_link(
        page,
        label=label or page.title,
        icon=page.icon,
        use_container_width=True,
    )


def render_primary_navigation(
    refs: Mapping[str, st.Page],
    selected_key: str,
) -> None:
    """Render one route model as desktop sidebar and mobile bottom bar."""

    with st.sidebar:
        st.markdown("## IELTS AI Coach")
        st.caption("专注、清晰、每天进步一点")
        for section, keys in (
            ("练习", PRIMARY_NAVIGATION_KEYS[:5]),
            ("学习", PRIMARY_NAVIGATION_KEYS[5:7]),
            ("账户", PRIMARY_NAVIGATION_KEYS[7:]),
        ):
            st.caption(section)
            for key in keys:
                _render_link(refs[key])

    with st.container(key="mobile_bottom_navigation"):
        columns = st.columns(5)
        mobile_items = (
            ("home", "首页"),
            ("reading", "阅读"),
            ("writing", "写作"),
            ("plan", "计划"),
        )
        for column, (key, label) in zip(columns[:4], mobile_items):
            with column:
                _render_link(refs[key], label=label)
        with columns[4]:
            with st.popover("更多", use_container_width=True):
                for key in ("listening", "speaking", "history", "profile"):
                    _render_link(refs[key])

    st.session_state["active_primary_route"] = selected_key


def run_hidden_navigation(pages: Sequence[st.Page]) -> None:
    """Run the hidden Streamlit router behind the custom shell."""

    selected_page = st.navigation(pages, position="hidden")
    selected_page.run()
