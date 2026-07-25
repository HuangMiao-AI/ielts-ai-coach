"""Streamlit contracts for persistent four-step learner onboarding."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ielts_ai_coach.services.learner_profiles import get_learner_profile
from tests.ui_page_helpers import open_authenticated_page


def _button(app: AppTest, label: str):
    """Return one visible button by exact label."""

    return next(item for item in app.button if item.label == label)


def _text_input(app: AppTest, label: str):
    """Return one visible text input by exact label."""

    return next(item for item in app.text_input if item.label == label)


def _selectbox(app: AppTest, label: str):
    """Return one visible select box by exact label."""

    return next(item for item in app.selectbox if item.label == label)


def _advance_basic_step(app: AppTest, display_name: str = "新同学") -> AppTest:
    """Complete the first onboarding step."""

    _text_input(app, "姓名或昵称").input(display_name)
    _selectbox(app, "当前年级或阶段").select("高二")
    return _button(app, "下一步").click().run(timeout=10)


def _advance_optional_scores(
    app: AppTest,
    *,
    reading: float | None = None,
    writing: float | None = None,
) -> AppTest:
    """Complete the optional score step with selectable partial evidence."""

    if reading is not None:
        _selectbox(app, "当前阅读成绩").select(reading)
    if writing is not None:
        _selectbox(app, "当前写作成绩").select(writing)
    return _button(app, "下一步").click().run(timeout=10)


def _advance_goals(app: AppTest) -> AppTest:
    """Accept valid default goals with an explicitly absent exam date."""

    assert next(
        item
        for item in app.checkbox
        if item.label == "暂未确定考试日期"
    ).value is True
    return _button(app, "下一步").click().run(timeout=10)


def test_onboarding_saves_all_missing_scores_and_switches_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new user may omit scores/date and arrives at Home after save."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="profile",
        username="OnboardingEmpty",
    )
    assert app.title[0].value == "开始设置学习档案"
    assert any("步骤 1/4" in item.value for item in app.caption)

    app = _advance_basic_step(app)
    assert any("步骤 2/4" in item.value for item in app.caption)
    assert _selectbox(app, "当前听力成绩").value == "未填写"
    assert _selectbox(app, "当前阅读成绩").value == "未填写"
    assert _selectbox(app, "当前写作成绩").value == "未填写"
    assert _selectbox(app, "当前口语成绩").value == "未填写"

    app = _advance_optional_scores(app)
    assert any("步骤 3/4" in item.value for item in app.caption)
    app = _advance_goals(app)
    assert any("步骤 4/4" in item.value for item in app.caption)

    app = _button(app, "保存并进入首页").click().run(timeout=10)

    assert app.title[0].value.startswith("你好，")
    assert any("资料已保存" in item.value for item in app.success)
    saved = get_learner_profile(app.session_state["user_id"])
    assert saved is not None
    assert saved.onboarding_completed is True
    assert saved.exam_date is None
    assert saved.current_listening_band is None
    assert saved.current_reading_band is None
    assert saved.current_writing_band is None
    assert saved.current_speaking_band is None


def test_onboarding_preserves_partial_scores_without_filling_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the score controls a user selected become measured baselines."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="profile",
        username="OnboardingPartial",
    )
    app = _advance_basic_step(app, "部分成绩")
    app = _advance_optional_scores(app, reading=6.5, writing=5.5)
    app = _advance_goals(app)
    app = _button(app, "保存并进入首页").click().run(timeout=10)

    saved = get_learner_profile(app.session_state["user_id"])
    assert saved is not None
    assert saved.current_reading_band == 6.5
    assert saved.current_writing_band == 5.5
    assert saved.current_listening_band is None
    assert saved.current_speaking_band is None


def test_completed_onboarding_persists_in_a_fresh_streamlit_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refresh resolves V2 completion and does not reopen onboarding."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="profile",
        username="OnboardingRefresh",
    )
    app = _advance_basic_step(app)
    app = _advance_optional_scores(app)
    app = _advance_goals(app)
    app = _button(app, "保存并进入首页").click().run(timeout=10)
    user_id = app.session_state["user_id"]

    refreshed = AppTest.from_file("app.py")
    refreshed.session_state["authenticated"] = True
    refreshed.session_state["user_id"] = user_id
    refreshed.session_state["username"] = "OnboardingRefresh"
    refreshed.run(timeout=10)

    assert refreshed.title[0].value.startswith("你好，")
    assert not any(
        title.value == "开始设置学习档案" for title in refreshed.title
    )


def test_completed_profile_and_settings_expose_optional_score_editors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both approved settings surfaces expose the shared baseline fields."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="profile",
        username="ProfileEditor",
    )
    app = _advance_basic_step(app)
    app = _advance_optional_scores(app)
    app = _advance_goals(app)
    app = _button(app, "保存并进入首页").click().run(timeout=10)

    from streamlit.navigation.page import calc_hash

    app._page_hash = calc_hash("profile")
    app.run(timeout=10)
    assert app.title[0].value == "我的档案"
    assert _selectbox(app, "当前阅读成绩").value == "未填写"

    app._page_hash = calc_hash("settings")
    app.run(timeout=10)
    assert any(
        item.value == "学习设置" for item in app.subheader
    )
    assert _selectbox(app, "当前口语成绩").value == "未填写"

