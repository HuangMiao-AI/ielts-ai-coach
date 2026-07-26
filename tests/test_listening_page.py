"""Student-facing flow for bundled original Listening mini tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ielts_ai_coach.services.exam_controls import (
    ExamStatus,
    exam_control_key,
    restore_exam_session,
)
from ielts_ai_coach.services.listening_bank import load_listening_bank
from tests.ui_page_helpers import open_authenticated_page


def _button(app, label: str):
    """Return one visible button with an exact label."""

    return next(button for button in app.button if button.label == label)


def test_listening_page_exposes_original_tests_and_audio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Listening is a usable local test library rather than a Demo shell."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="listening",
        username="ListeningLibrary",
    )

    assert not app.exception
    assert app.title[0].value == "听力练习"
    assert len([button for button in app.button if "开始 Test" in button.label]) == 2
    assert "Demo 模式" not in "\n".join(item.value for item in app.caption)
    assert "原创 IELTS 风格练习" in "\n".join(
        item.value for item in app.caption
    )


def test_listening_submission_scores_and_reveals_review_only_after_confirm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A complete answer set receives deterministic session-only review."""

    test = load_listening_bank().tests[0]
    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="listening",
        username="ListeningSubmit",
    )
    app = _button(app, "开始 Test 1").click().run(timeout=10)

    assert not app.exception
    assert len(app.get("audio")) == 1
    assert not any("正确答案" in item.value for item in app.markdown)
    for index, question in enumerate(test.questions):
        if question.question_type == "multiple_choice":
            app.radio[0].set_value(question.correct_answer).run(timeout=10)
        else:
            app.text_input[0].input(question.correct_answer).run(timeout=10)
        if index < len(test.questions) - 1:
            app = _button(app, "下一题").click().run(timeout=10)

    app = _button(app, "检查并提交").click().run(timeout=10)
    assert any("提交后无法修改" in item.value for item in app.warning)
    assert not any("正确答案" in item.value for item in app.markdown)
    app = _button(app, "确认提交").click().run(timeout=10)

    assert not app.exception
    assert any(metric.label == "总分" and metric.value == "16/16" for metric in app.metric)
    assert any("正确答案" in item.value for item in app.markdown)
    assert any("结果仅保存在当前会话" in item.value for item in app.caption)


def test_listening_shared_controls_pause_resume_and_submit_after_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Listening locks answer widgets and permits timeout hand-in once."""

    test = load_listening_bank().tests[0]
    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="listening",
        username="ListeningControls",
    )
    app = _button(app, "开始 Test 1").click().run(timeout=10)

    assert not any("剩余" in item.value for item in app.caption)
    app = _button(app, "暂停计时").click().run(timeout=10)
    answer_widgets = [*app.radio, *app.text_input]
    assert answer_widgets
    assert all(item.disabled for item in answer_widgets)
    assert any("计时已暂停" in item.value for item in app.info)

    app = _button(app, "恢复计时").click().run(timeout=10)
    assert all(not item.disabled for item in [*app.radio, *app.text_input])

    key = exam_control_key(
        app.session_state["user_id"],
        "listening",
        test.test_id,
    )
    payload = dict(app.session_state[key])
    payload["deadline"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    app.session_state[key] = payload
    app = app.run(timeout=10)

    assert all(item.disabled for item in [*app.radio, *app.text_input])
    assert any("时间已到" in item.value for item in app.warning)
    app = _button(app, str(len(test.questions))).click().run(timeout=10)
    app = _button(app, "检查并提交").click().run(timeout=10)
    assert any("未作答题目将在交卷后计为错误" in item.value for item in app.warning)
    app = _button(app, "确认提交").click().run(timeout=10)

    assert any(metric.label == "总分" for metric in app.metric)
    assert restore_exam_session(app.session_state[key]).status is (
        ExamStatus.SUBMITTED
    )
