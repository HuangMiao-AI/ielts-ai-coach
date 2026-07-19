"""Streamlit page flow for starting, continuing, and submitting reading."""

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
from ielts_ai_coach.services.reading_practice import (
    get_reading_practice_state,
)
from ielts_ai_coach.services.scores import save_score_record


def _button(app: AppTest, label: str):
    """Return the first visible button with an exact label."""

    return next(button for button in app.button if button.label == label)


def test_today_reading_action_opens_the_dedicated_exam_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Today's task must hand off to the dedicated user-owned exam route."""

    database_url = f"sqlite:///{(tmp_path / 'reading-flow.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    initialize_database(database_url)
    factory = get_session_factory(database_url)
    today = date.today()
    user_id = register_user(
        "ReadingPageStudent",
        "secure-pass-01",
        state={},
        session_factory=factory,
    ).id
    save_profile(
        user_id=user_id,
        nickname="阅读同学",
        grade="高二",
        target_overall=7.0,
        exam_date=today + timedelta(days=60),
        daily_study_minutes=120,
        today=today,
        session_factory=factory,
    )
    save_score_record(
        user_id=user_id,
        scores={
            "listening": 6.5,
            "reading": 5.0,
            "writing": 6.5,
            "speaking": 6.5,
        },
        session_factory=factory,
    )
    plan = generate_plan(user_id, today=today, session_factory=factory)
    reading_task = next(
        task
        for task in plan.tasks
        if task.subject == "reading" and task.task_date == today
    )
    state = get_reading_practice_state(
        user_id=user_id,
        task_id=reading_task.id,
        session_factory=factory,
    )
    assert state is not None

    app = AppTest.from_file("app.py")
    app.session_state["authenticated"] = True
    app.session_state["user_id"] = user_id
    app.session_state["username"] = "ReadingPageStudent"
    app.run(timeout=10)
    app._page_hash = calc_hash("today")
    app.run(timeout=10)

    assert not app.exception
    assert not any("正确答案：" in item.value for item in app.markdown)
    _button(app, "开始练习").click().run(timeout=10)
    assert not app.exception
    assert app.title[0].value == state.passage.title
    assert any(item.value == "考试说明" for item in app.subheader)
    assert len(app.radio) == 0
    assert not any("正确答案：" in item.value for item in app.markdown)
    assert app.session_state[f"reading_selected_task_{user_id}"] == reading_task.id
