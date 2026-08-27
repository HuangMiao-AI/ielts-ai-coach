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
WORKSPACE_SOURCE = (
    PROJECT_ROOT / "ielts_ai_coach" / "views" / "reading_workspace.py"
)
WORKSPACE_CLIENT_SOURCE = (
    PROJECT_ROOT
    / "ielts_ai_coach"
    / "views"
    / "reading_workspace_client.py"
)
EXAM_CONTROL_PANEL_SOURCE = (
    PROJECT_ROOT / "ielts_ai_coach" / "views" / "exam_control_panel.py"
)
EXAM_TIMER_CLIENT_SOURCE = (
    PROJECT_ROOT
    / "ielts_ai_coach"
    / "components"
    / "exam_timer"
    / "frontend"
    / "index.html"
)
LOGIN_SOURCE = PROJECT_ROOT / "ielts_ai_coach" / "views" / "login.py"


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
    app.button[2].click()
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
        "reading": "阅读练习",
        "listening": "听力练习",
        "plan": "七天计划",
        "coach": "AI学习教练",
        "writing": "写作练习",
        "speaking": "口语练习",
        "profile": "开始设置学习档案",
        "history": "历史记录",
        "settings": "设置",
    }

    assert NAVIGATION_STRUCTURE == {
        "练习": ("首页", "阅读", "听力", "写作", "口语"),
        "学习": ("学习计划", "历史记录"),
        "账户": ("个人资料",),
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
    assert app.title[0].value == "写作练习"
    assert prompt.value
    assert any("已从今日任务带入原创题目" in item.value for item in app.success)


def test_mobile_css_uses_safe_responsive_navigation_and_overflow() -> None:
    """Responsive rules must preserve compact cards and safe mobile actions."""

    route_source = (
        PROJECT_ROOT
        / "ielts_ai_coach"
        / "views"
        / "navigation.py"
    ).read_text(encoding="utf-8")
    navigation_source = (
        PROJECT_ROOT
        / "ielts_ai_coach"
        / "ui"
        / "navigation.py"
    ).read_text(encoding="utf-8")
    workspace_source = (
        PROJECT_ROOT
        / "ielts_ai_coach"
        / "views"
        / "reading_workspace.py"
    ).read_text(encoding="utf-8")
    resizer_source = (
        PROJECT_ROOT
        / "ielts_ai_coach"
        / "views"
        / "reading_workspace_resizer.py"
    ).read_text(encoding="utf-8")

    assert 'position="hidden"' in navigation_source
    assert "st.sidebar" in navigation_source
    assert "mobile_bottom_navigation" in navigation_source
    assert "run_hidden_navigation" in route_source
    assert "@media (max-width: 768px)" in APP_CSS
    assert ".st-key-mobile_bottom_navigation" in APP_CSS
    assert 'data-testid="stHorizontalBlock"' in APP_CSS
    assert "env(safe-area-inset-bottom)" in APP_CSS
    assert (
        '.st-key-mobile_bottom_navigation [data-testid="stColumn"]'
        in APP_CSS
    )
    assert "flex: 1 1 0 !important" in APP_CSS
    assert "overflow-x: hidden" in APP_CSS
    assert "overflow-x: clip" not in APP_CSS
    assert ".growth-dashboard-grid" in APP_CSS
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in APP_CSS
    assert "@media (max-width: 768px)" in APP_CSS
    assert "grid-template-columns: 1fr" in APP_CSS
    assert "@media (max-width: 430px)" in APP_CSS
    assert "gap: .65rem" in APP_CSS
    assert "min-width: 0" in APP_CSS
    assert "calc(5.5rem + env(safe-area-inset-bottom))" in APP_CSS
    assert "min-height: 44px" in APP_CSS
    assert ".reading-workspace-status" in APP_CSS
    assert ".exam-control-status" in APP_CSS
    assert ".reading-question-navigation" in APP_CSS
    assert ".reading-question-link.answered" in APP_CSS
    assert ".reading-question-link.current" in APP_CSS
    current_rule = APP_CSS.split(
        ".reading-question-link.current",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "outline" not in current_rule
    assert "box-shadow" not in current_rule
    assert ".reading-workspace" in APP_CSS
    assert "overflow-y: auto" in APP_CSS
    assert "render_workspace_resizer" in workspace_source
    assert "localStorage" in resizer_source
    assert "pointermove" in resizer_source
    assert "0.35" in resizer_source
    assert "0.65" in resizer_source
    assert APP_CSS.count("overflow-x:") == 2
    assert "userAgent" not in APP_CSS
    assert "iPhone" not in APP_CSS
    assert "Android" not in APP_CSS


def test_reading_workspace_declares_a_wall_clock_client_timer() -> None:
    """The visible clock must not wait for a Streamlit rerun to change."""

    workspace_source = WORKSPACE_SOURCE.read_text(encoding="utf-8")
    panel_source = EXAM_CONTROL_PANEL_SOURCE.read_text(encoding="utf-8")
    client_source = EXAM_TIMER_CLIENT_SOURCE.read_text(encoding="utf-8")

    assert "render_exam_control_panel" in workspace_source
    assert "data-exam-control" in panel_source
    assert "render_exam_timer" in panel_source
    assert "Date.now()" in client_source
    assert "visibilitychange" in client_source
    assert "Math.max(0" in client_source
    assert "setInterval" in client_source
    assert 'addEventListener("pagehide", teardown' in client_source


def test_question_navigation_declares_client_click_and_scroll_sync() -> None:
    """Question links must track visible questions without scroll reruns."""

    workspace_source = WORKSPACE_SOURCE.read_text(encoding="utf-8")
    client_source = WORKSPACE_CLIENT_SOURCE.read_text(encoding="utf-8")

    assert "data-reading-question-id" in workspace_source
    assert "render_reading_navigation_client" in workspace_source
    assert "IntersectionObserver" in client_source
    assert "scrollIntoView" in client_source
    assert "aria-current" in client_source
    assert "localStorage" in client_source


def test_auth_page_uses_one_centered_mobile_form_shell() -> None:
    """Mobile authentication must not inherit desktop spacer columns."""

    login_source = LOGIN_SOURCE.read_text(encoding="utf-8")

    assert 'key="auth_form_shell"' in login_source
    assert "st.columns([1, 1.35, 1])" not in login_source
    assert ".st-key-auth_form_shell" in APP_CSS
    assert "max-width: 420px" in APP_CSS
