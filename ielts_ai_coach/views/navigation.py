"""Route registry for the authenticated Streamlit application."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.profiles import get_profile
from ielts_ai_coach.ui.layout import render_page_shell
from ielts_ai_coach.ui.navigation import (
    CONTEXTUAL_ROUTE_KEYS,
    PRIMARY_NAVIGATION_KEYS,
    run_hidden_navigation,
)
from ielts_ai_coach.views.coach import render_coach_page
from ielts_ai_coach.views.dashboard import render_dashboard
from ielts_ai_coach.views.history import render_history_page
from ielts_ai_coach.views.listening import render_listening_page
from ielts_ai_coach.views.plan import render_plan_page
from ielts_ai_coach.views.profile import render_profile_page
from ielts_ai_coach.views.reading import render_reading_page
from ielts_ai_coach.views.scores import render_scores_page
from ielts_ai_coach.views.settings import render_settings_page
from ielts_ai_coach.views.speaking import render_speaking_page
from ielts_ai_coach.views.today import render_today_page
from ielts_ai_coach.views.writing import render_writing_page


NAVIGATION_STRUCTURE = {
    "练习": ("首页", "阅读", "听力", "写作", "口语"),
    "学习": ("学习计划", "历史记录"),
    "账户": ("个人资料",),
}

_ROUTE_META = {
    "home": ("首页", ":material/home:"),
    "reading": ("阅读", ":material/menu_book:"),
    "listening": ("听力", ":material/headphones:"),
    "writing": ("写作", ":material/edit_note:"),
    "speaking": ("口语", ":material/mic:"),
    "plan": ("学习计划", ":material/calendar_month:"),
    "history": ("历史记录", ":material/history:"),
    "profile": ("个人资料", ":material/person:"),
    "scores": ("成绩诊断", ":material/monitoring:"),
    "today": ("今日任务", ":material/check_circle:"),
    "coach": ("AI 学习教练", ":material/forum:"),
    "settings": ("设置", ":material/settings:"),
}


def _page(
    renderer: Callable[[], None],
    *,
    key: str,
    default: bool = False,
) -> st.Page:
    """Create one Streamlit route from shared metadata."""

    title, icon = _ROUTE_META[key]
    return st.Page(
        renderer,
        title=title,
        icon=icon,
        url_path=key,
        default=default,
    )


def build_navigation_pages(
    user: User,
    *,
    has_profile: bool,
) -> tuple[list[st.Page], dict[str, st.Page]]:
    """Build visible and contextual routes from one registry."""

    refs: dict[str, st.Page] = {}
    context: dict[str, object] = {}

    def wrapped(renderer: Callable[[], None], key: str) -> Callable[[], None]:
        """Bind shared route chrome to one page renderer."""

        return partial(
            _run_page,
            renderer,
            user,
            context,
            key,
            not has_profile,
        )

    renderers: dict[str, Callable[[], None]] = {
        "home": partial(render_dashboard, user, refs),
        "reading": partial(render_reading_page, user, refs),
        "listening": partial(render_listening_page, user),
        "writing": partial(render_writing_page, user),
        "speaking": partial(render_speaking_page, user),
        "plan": partial(render_plan_page, user),
        "history": partial(render_history_page, user),
        "profile": partial(render_profile_page, user),
        "scores": partial(render_scores_page, user),
        "today": partial(render_today_page, user, refs),
        "coach": partial(render_coach_page, user),
        "settings": partial(render_settings_page, user),
    }
    for key in (*PRIMARY_NAVIGATION_KEYS, *CONTEXTUAL_ROUTE_KEYS):
        refs[key] = _page(
            wrapped(renderers[key], key),
            key=key,
            default=(
                (key == "home" and has_profile)
                or (key == "profile" and not has_profile)
            ),
        )

    context["refs"] = refs
    pages = [
        refs[key] for key in (*PRIMARY_NAVIGATION_KEYS, *CONTEXTUAL_ROUTE_KEYS)
    ]
    return pages, refs


def _run_page(
    renderer: Callable[[], None],
    user: User,
    context: dict[str, object],
    route_key: str,
    show_profile_warning: bool,
) -> None:
    """Render shared chrome and the selected route."""

    refs = context["refs"]
    render_page_shell(
        user,
        refs,  # type: ignore[arg-type]
        route_key,
        show_profile_warning=show_profile_warning,
    )
    renderer()


def render_authenticated_app(user: User) -> None:
    """Run the selected route behind the custom responsive navigation."""

    profile = get_profile(user.id)
    pages, _ = build_navigation_pages(user, has_profile=profile is not None)
    run_hidden_navigation(pages)
