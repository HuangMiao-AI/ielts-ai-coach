"""Contracts for the resilient Writing editor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ielts_ai_coach.services.exam_controls import (
    ExamStatus,
    exam_control_key,
    restore_exam_session,
)
from ielts_ai_coach.services.skill_sessions import draft_key
from tests.ui_page_helpers import open_authenticated_page

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_writing_editor_uses_live_isolated_drafts_and_submit_guard() -> None:
    """Task drafts, live count, clear confirmation, and submit lock are required."""

    source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "writing.py"
    ).read_text(encoding="utf-8")
    actions_source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "writing_actions.py"
    ).read_text(encoding="utf-8")

    assert "st.form(" not in source
    assert "draft_key(" in source
    assert "count_words(content)" in source
    assert "确认清空当前草稿" in actions_source
    assert "claim_submission(" in actions_source
    assert "release_submission(" in actions_source


def test_writing_editor_updates_word_count_and_requires_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Editing is live and the first submit click never calls the provider."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="writing",
        username="WritingEditor",
    )
    prompt = next(area for area in app.text_area if area.label == "作文题目")
    content = next(area for area in app.text_area if area.label == "作文正文")
    prompt.input("Discuss whether practical skills belong in schools.")
    content.input("One two three four five.").run(timeout=10)

    assert any("当前字数：5词" in item.value for item in app.caption)
    next(
        button for button in app.button if button.label == "保存作文"
    ).click().run(timeout=10)
    assert any("不会生成AI评分" in item.value for item in app.warning)
    assert not any(metric.label == "预估总分" for metric in app.metric)


def test_writing_shared_controls_lock_editor_and_submit_after_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Writing uses the shared pause, resume, timeout, and submit lifecycle."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="writing",
        username="WritingControls",
    )
    content = next(area for area in app.text_area if area.label == "作文正文")
    app = content.input(
        "Public classes help families learn together. "
        "They also make community spaces more useful."
    ).run(timeout=10)

    app = next(
        button for button in app.button if button.label == "暂停计时"
    ).click().run(timeout=10)
    assert all(area.disabled for area in app.text_area)
    app = next(
        button for button in app.button if button.label == "恢复考试"
    ).click().run(timeout=10)
    assert all(not area.disabled for area in app.text_area)
    resumed_content = next(
        area for area in app.text_area if area.label == "作文正文"
    )
    resume_value_key = (
        f"{draft_key(app.session_state['user_id'], 'writing', 'WRITE-V1-A1-LINE')}"
        "_content_value"
    )
    resume_value = (
        app.session_state[resume_value_key]
        if resume_value_key in app.session_state
        else None
    )
    assert "Public classes" in resumed_content.value, resume_value

    key = exam_control_key(
        app.session_state["user_id"],
        "writing",
        "WRITE-V1-A1-LINE",
    )
    payload = dict(app.session_state[key])
    payload["deadline"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    app.session_state[key] = payload
    app = app.run(timeout=10)

    assert all(area.disabled for area in app.text_area)
    assert any("时间已到" in item.value for item in app.warning)
    content_value_key = (
        f"{draft_key(app.session_state['user_id'], 'writing', 'WRITE-V1-A1-LINE')}"
        "_content_value"
    )
    assert "Public classes" in app.session_state[content_value_key]
    app = next(
        button for button in app.button if button.label == "保存作文"
    ).click().run(timeout=10)
    app = next(
        button for button in app.button if button.label == "确认保存作文"
    ).click().run(timeout=10)

    assert not app.exception
    assert not app.error, [item.value for item in app.error]
    assert any("作文已保存" in item.value for item in app.success)
    control = restore_exam_session(app.session_state[key])
    assert control.status is ExamStatus.SUBMITTED
