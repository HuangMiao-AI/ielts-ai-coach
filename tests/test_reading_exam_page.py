"""End-to-end Streamlit flow for the dedicated Reading exam page."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from streamlit.navigation.page import calc_hash
from streamlit.testing.v1 import AppTest

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.connection import (
    get_session_factory,
    initialize_database,
)
from ielts_ai_coach.database.models import TaskQuestionAttempt
from ielts_ai_coach.services.planning import generate_plan
from ielts_ai_coach.services.profiles import save_profile
from ielts_ai_coach.services.reading_practice import get_reading_practice_state
from ielts_ai_coach.services.scores import save_score_record


def _button(app: AppTest, label: str):
    """Return the first visible button with an exact label."""

    return next(button for button in app.button if button.label == label)


def _prepare_reading_app(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[AppTest, object, int]:
    """Create an isolated reader and open the dedicated Reading route."""

    database_url = f"sqlite:///{(tmp_path / 'exam-page.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    initialize_database(database_url)
    factory = get_session_factory(database_url)
    today = date.today()
    user_id = register_user(
        "ExamPageStudent",
        "secure-pass-01",
        state={},
        session_factory=factory,
    ).id
    save_profile(
        user_id=user_id,
        nickname="阅读考生",
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
    task = next(item for item in plan.tasks if item.subject == "reading")
    state = get_reading_practice_state(
        user_id=user_id,
        task_id=task.id,
        session_factory=factory,
    )
    assert state is not None

    app = AppTest.from_file("app.py")
    app.session_state["authenticated"] = True
    app.session_state["user_id"] = user_id
    app.session_state["username"] = "ExamPageStudent"
    app.run(timeout=10)
    app._page_hash = calc_hash("reading")
    return app.run(timeout=10), state, task.id


def test_reading_exam_hides_answers_until_confirmed_submission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Library, exam, confirmation, result, and review must form one loop."""

    app, practice, task_id = _prepare_reading_app(tmp_path, monkeypatch)

    assert not app.exception
    assert app.title[0].value == "阅读练习"
    assert not any("正确答案：" in item.value for item in app.markdown)
    _button(app, "开始练习").click().run(timeout=10)
    assert any(item.value == "考试说明" for item in app.subheader)
    _button(app, "开始计时练习").click().run(timeout=10)

    for index, question in enumerate(practice.passage.questions):
        assert len(app.radio) == 1
        app.radio[0].set_value(question.correct_answer).run(timeout=10)
        assert not any("正确答案：" in item.value for item in app.markdown)
        if index < len(practice.passage.questions) - 1:
            _button(app, "下一题").click().run(timeout=10)

    _button(app, "检查并提交").click().run(timeout=10)
    assert any("提交后无法修改" in item.value for item in app.warning)
    assert not any("正确答案：" in item.value for item in app.markdown)
    _button(app, "确认提交").click().run(timeout=10)

    assert not app.exception
    assert any(metric.label == "总分" for metric in app.metric)
    assert any(metric.label == "正确率" for metric in app.metric)
    assert not any("正确答案：" in item.value for item in app.markdown)
    _button(app, "查看逐题解析").click().run(timeout=10)
    assert any("正确答案：" in item.value for item in app.markdown)

    factory = get_session_factory()
    with factory() as session:
        assert int(
            session.scalar(
                select(func.count()).select_from(TaskQuestionAttempt)
            )
            or 0
        ) == 1
    assert app.session_state[f"reading_selected_task_{practice.task.user_id}"] == task_id

    app._page_hash = calc_hash("history")
    app.run(timeout=10)
    assert any(item.value == "阅读练习记录" for item in app.subheader)
    assert not any("正确答案：" in item.value for item in app.markdown)
    _button(app, "查看完整解析").click().run(timeout=10)
    assert any("正确答案：" in item.value for item in app.markdown)
