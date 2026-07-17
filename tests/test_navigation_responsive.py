"""Tests for top navigation, writing handoff, and responsive CSS."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.navigation.page import calc_hash
from streamlit.testing.v1 import AppTest

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.connection import (
    get_session_factory,
    initialize_database,
)
from ielts_ai_coach.services.planning import generate_plan
from ielts_ai_coach.services.profiles import save_profile
from ielts_ai_coach.services.scores import save_score_record
from ielts_ai_coach.ui.styles import APP_CSS
from ielts_ai_coach.views.navigation import NAVIGATION_STRUCTURE


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _configure_app(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
) -> str:
    """Configure one isolated application database."""

    database_url = f"sqlite:///{(tmp_path / filename).as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    initialize_database(database_url)
    return database_url


def _register_through_ui(app: AppTest, username: str) -> AppTest:
    """Register through UI, then return a clean authenticated test session."""

    app.text_input[2].input(username)
    app.text_input[3].input("secure-pass-01")
    app.text_input[4].input("secure-pass-01")
    app.button[1].click()
    registered_app = app.run(timeout=10)
    authenticated_app = AppTest.from_file("app.py")
    authenticated_app.session_state["authenticated"] = True
    authenticated_app.session_state["user_id"] = registered_app.session_state[
        "user_id"
    ]
    authenticated_app.session_state["username"] = username
    return authenticated_app.run(timeout=10)


def _open_page(app: AppTest, url_path: str) -> AppTest:
    """Open a callable page using its registered top-navigation path."""

    app._page_hash = calc_hash(url_path)
    return app.run(timeout=10)


def test_top_navigation_groups_and_every_page_opens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every grouped top-navigation destination must render independently."""

    _configure_app(tmp_path, monkeypatch, "navigation.db")
    app = _register_through_ui(
        AppTest.from_file("app.py").run(timeout=10),
        "NavigationStudent",
    )
    expected_titles = {
        "home": "你好，NavigationStudent",
        "scores": "成绩诊断",
        "today": "今日任务",
        "plan": "七天计划",
        "coach": "AI学习教练",
        "writing": "写作批改",
        "profile": "我的档案",
        "history": "历史记录",
        "settings": "设置",
    }

    assert NAVIGATION_STRUCTURE == {
        "学习": ("首页", "成绩诊断", "今日任务", "七天计划"),
        "AI工具": ("AI学习教练", "写作批改"),
        "我的": ("我的档案", "历史记录", "设置"),
    }
    for path, title in expected_titles.items():
        _open_page(app, path)
        assert not app.exception
        assert app.title[0].value == title


def test_writing_task_opens_feedback_page_with_prefilled_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A concrete writing task must hand its prompt to the writing form."""

    database_url = _configure_app(tmp_path, monkeypatch, "prefill.db")
    factory = get_session_factory(database_url)
    today = date.today()
    user_id = register_user(
        "WritingHandoff",
        "secure-pass-01",
        state={},
        session_factory=factory,
    ).id
    save_profile(
        user_id=user_id,
        nickname="写作同学",
        grade="高二",
        target_overall=7.0,
        exam_date=today + timedelta(days=60),
        daily_study_minutes=90,
        today=today,
        session_factory=factory,
    )
    save_score_record(
        user_id=user_id,
        scores={
            "listening": 6.5,
            "reading": 6.5,
            "writing": 5.0,
            "speaking": 6.5,
        },
        session_factory=factory,
    )
    generate_plan(user_id, today=today, session_factory=factory)

    app = AppTest.from_file("app.py")
    app.session_state["authenticated"] = True
    app.session_state["user_id"] = user_id
    app.session_state["username"] = "WritingHandoff"
    app.run(timeout=10)
    _open_page(app, "today")
    handoff = next(
        button
        for button in app.button
        if button.label == "带题目去写作批改"
    )
    handoff.click().run(timeout=10)

    prompt = next(
        area for area in app.text_area if area.label == "作文题目"
    )
    assert not app.exception
    assert app.title[0].value == "写作批改"
    assert prompt.value
    assert any("已从今日任务带入原创题目" in item.value for item in app.success)


def test_mobile_css_stacks_content_and_prevents_page_overflow() -> None:
    """Responsive rules must use viewport width and avoid device detection."""

    navigation_source = (
        PROJECT_ROOT
        / "ielts_ai_coach"
        / "views"
        / "navigation.py"
    ).read_text(encoding="utf-8")

    assert 'position="top"' in navigation_source
    assert "st.sidebar" not in navigation_source
    assert "mobile_quick_navigation" in navigation_source
    assert "@media (max-width: 768px)" in APP_CSS
    assert ".st-key-mobile_quick_navigation" in APP_CSS
    assert 'data-testid="stHorizontalBlock"' in APP_CSS
    assert "flex-direction: column !important" in APP_CSS
    assert "overflow-x: clip" in APP_CSS
    assert "text-overflow: clip" in APP_CSS
    assert "userAgent" not in APP_CSS
    assert "iPhone" not in APP_CSS
    assert "Android" not in APP_CSS
