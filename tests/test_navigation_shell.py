"""Contracts for the single responsive application navigation shell."""

from __future__ import annotations

from pathlib import Path

from ielts_ai_coach.ui.navigation import (
    CONTEXTUAL_ROUTE_KEYS,
    PRIMARY_NAVIGATION_KEYS,
    PRIMARY_ROUTE_TITLES,
)
from ielts_ai_coach.views.navigation import NAVIGATION_STRUCTURE


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_primary_navigation_matches_the_student_information_architecture() -> None:
    """Only the approved student destinations belong in primary navigation."""

    assert PRIMARY_NAVIGATION_KEYS == (
        "home",
        "reading",
        "listening",
        "writing",
        "speaking",
        "plan",
        "history",
        "profile",
    )
    assert PRIMARY_ROUTE_TITLES == (
        "首页",
        "阅读",
        "听力",
        "写作",
        "口语",
        "学习计划",
        "历史记录",
        "个人资料",
    )
    assert len(PRIMARY_ROUTE_TITLES) == len(set(PRIMARY_ROUTE_TITLES))
    assert NAVIGATION_STRUCTURE == {
        "练习": ("首页", "阅读", "听力", "写作", "口语"),
        "学习": ("学习计划", "历史记录"),
        "账户": ("个人资料",),
    }
    assert CONTEXTUAL_ROUTE_KEYS == ("scores", "today", "coach", "settings")


def test_streamlit_router_is_hidden_behind_one_custom_navigation() -> None:
    """Desktop and mobile variants must share one route definition."""

    source = (
        PROJECT_ROOT / "ielts_ai_coach" / "ui" / "navigation.py"
    ).read_text(encoding="utf-8")

    assert 'position="hidden"' in source
    assert "st.sidebar" in source
    assert "mobile_bottom_navigation" in source
    assert 'position="top"' not in source
    assert "mobile_quick_navigation" not in source
