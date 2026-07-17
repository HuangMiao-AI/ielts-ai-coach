"""Grouped top navigation for the authenticated Streamlit application."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.profiles import get_profile
from ielts_ai_coach.views.coach import render_coach_page
from ielts_ai_coach.views.dashboard import render_dashboard
from ielts_ai_coach.views.history import render_history_page
from ielts_ai_coach.views.plan import render_plan_page
from ielts_ai_coach.views.profile import render_profile_page
from ielts_ai_coach.views.scores import render_scores_page
from ielts_ai_coach.views.settings import render_settings_page
from ielts_ai_coach.views.today import render_today_page
from ielts_ai_coach.views.writing import render_writing_page


NAVIGATION_STRUCTURE = {
    "学习": ("首页", "成绩诊断", "今日任务", "七天计划"),
    "AI工具": ("AI学习教练", "写作批改"),
    "我的": ("我的档案", "历史记录", "设置"),
}


def build_navigation_pages(
    user: User,
    *,
    has_profile: bool,
) -> tuple[dict[str, list[st.Page]], dict[str, st.Page]]:
    """Build grouped pages and reusable references for in-app links."""

    page_refs: dict[str, st.Page] = {}
    navigation_context: dict[str, object] = {}
    page_refs["home"] = st.Page(
        partial(
            _run_page,
            partial(render_dashboard, user, page_refs),
            user,
            navigation_context,
            "首页",
            not has_profile,
        ),
        title="首页",
        icon="🏠",
        url_path="home",
        default=has_profile,
    )
    page_refs["scores"] = st.Page(
        partial(
            _run_page,
            partial(render_scores_page, user),
            user,
            navigation_context,
            "成绩诊断",
            not has_profile,
        ),
        title="成绩诊断",
        icon="📊",
        url_path="scores",
    )
    page_refs["today"] = st.Page(
        partial(
            _run_page,
            partial(render_today_page, user, page_refs),
            user,
            navigation_context,
            "今日任务",
            not has_profile,
        ),
        title="今日任务",
        icon="✅",
        url_path="today",
    )
    page_refs["plan"] = st.Page(
        partial(
            _run_page,
            partial(render_plan_page, user),
            user,
            navigation_context,
            "七天计划",
            not has_profile,
        ),
        title="七天计划",
        icon="🗓️",
        url_path="plan",
    )
    page_refs["coach"] = st.Page(
        partial(
            _run_page,
            partial(render_coach_page, user),
            user,
            navigation_context,
            "AI学习教练",
            not has_profile,
        ),
        title="AI学习教练",
        icon="💬",
        url_path="coach",
    )
    page_refs["writing"] = st.Page(
        partial(
            _run_page,
            partial(render_writing_page, user),
            user,
            navigation_context,
            "写作批改",
            not has_profile,
        ),
        title="写作批改",
        icon="✍️",
        url_path="writing",
    )
    page_refs["profile"] = st.Page(
        partial(
            _run_page,
            partial(render_profile_page, user),
            user,
            navigation_context,
            "我的档案",
            not has_profile,
        ),
        title="我的档案",
        icon="👤",
        url_path="profile",
        default=not has_profile,
    )
    page_refs["history"] = st.Page(
        partial(
            _run_page,
            partial(render_history_page, user),
            user,
            navigation_context,
            "历史记录",
            not has_profile,
        ),
        title="历史记录",
        icon="🕘",
        url_path="history",
    )
    page_refs["settings"] = st.Page(
        partial(
            _run_page,
            partial(render_settings_page, user),
            user,
            navigation_context,
            "设置",
            not has_profile,
        ),
        title="设置",
        icon="⚙️",
        url_path="settings",
    )
    groups = {
        "学习": [
            page_refs["home"],
            page_refs["scores"],
            page_refs["today"],
            page_refs["plan"],
        ],
        "AI工具": [page_refs["coach"], page_refs["writing"]],
        "我的": [
            page_refs["profile"],
            page_refs["history"],
            page_refs["settings"],
        ],
    }
    navigation_context["groups"] = groups
    return groups, page_refs


def _render_mobile_navigation(
    groups: dict[str, list[st.Page]],
    selected_title: str,
) -> None:
    """Render an in-page fallback that is visible only on narrow screens."""

    with st.container(key="mobile_quick_navigation"):
        with st.expander("页面导航"):
            for group_name, pages in groups.items():
                st.caption(group_name)
                for page in pages:
                    if page.title == selected_title:
                        continue
                    if st.button(
                        page.title,
                        icon=page.icon,
                        width="stretch",
                        key=(
                            f"mobile_nav_{selected_title}_"
                            f"{page.title}"
                        ),
                    ):
                        st.switch_page(page)


def _run_page(
    renderer: Callable[[], None],
    user: User,
    navigation_context: dict[str, object],
    page_title: str,
    show_profile_warning: bool,
) -> None:
    """Render shared controls and one page inside its active page context."""

    groups = navigation_context["groups"]
    st.markdown(
        f'<div class="current-user">IELTS AI Coach · {user.username}</div>',
        unsafe_allow_html=True,
    )
    _render_mobile_navigation(groups, page_title)  # type: ignore[arg-type]
    if show_profile_warning:
        st.warning("请先完善学习档案，之后即可录入成绩并生成计划。")
    renderer()


def render_authenticated_app(user: User) -> None:
    """Render width-independent top navigation and the selected page."""

    profile = get_profile(user.id)
    groups, _ = build_navigation_pages(
        user,
        has_profile=profile is not None,
    )
    selected_page = st.navigation(groups, position="top")
    selected_page.run()
