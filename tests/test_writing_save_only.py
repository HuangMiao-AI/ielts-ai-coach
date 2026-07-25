"""No-provider Writing persistence without fabricated AI feedback."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.models import AIUsageDaily, Essay, WritingFeedback
from ielts_ai_coach.services.writing import (
    get_essay_feedback,
    get_essay_history,
    get_writing_remaining,
    save_essay_without_feedback,
)
from ielts_ai_coach.services.writing_tasks import (
    inspect_writing_locally,
    load_writing_tasks,
)
from tests.ui_page_helpers import open_authenticated_page


def _user_id(session_factory, username: str) -> int:
    """Create one isolated Writing test user."""

    return register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id


def test_original_writing_tasks_and_local_checks_have_no_band() -> None:
    """Bundled tasks are original and local checks report structure only."""

    bank = load_writing_tasks()

    assert bank.source_type == "project_original"
    assert bank.is_official_ielts_content is False
    assert "非官方 IELTS 或 Cambridge" in bank.copyright_notice
    assert {task.task_type for task in bank.tasks} == {"Task 1", "Task 2"}
    assert {task.test_type for task in bank.tasks} == {"Academic", "General"}
    assert all(task.prompt and task.minimum_words in {150, 250} for task in bank.tasks)
    checks = inspect_writing_locally(
        "This is an introduction.\n\nThis paragraph develops the idea.\n\n"
        "In conclusion, the proposal is practical.",
        minimum_words=5,
    )
    assert checks.word_count > 5
    assert checks.paragraph_count == 3
    assert checks.meets_recommended_length is True
    assert checks.has_introduction is True
    assert checks.has_conclusion is True
    assert not hasattr(checks, "band")


def test_save_only_essay_creates_no_feedback_or_usage(
    session_factory,
) -> None:
    """Saving in disabled-AI mode preserves history without consuming quota."""

    user_id = _user_id(session_factory, "WritingSaveOnly")
    remaining_before = get_writing_remaining(
        user_id,
        session_factory=session_factory,
    )

    essay = save_essay_without_feedback(
        user_id=user_id,
        test_type="Academic",
        task_type="Task 2",
        prompt="Discuss whether cities should create more public gardens.",
        content=(
            "Public gardens improve daily life. They create quiet places and "
            "support local wildlife.\n\nIn conclusion, cities should reserve "
            "more land for accessible gardens."
        ),
        session_factory=session_factory,
    )

    assert essay.status == "saved"
    assert get_essay_history(user_id, session_factory=session_factory)[0].id == essay.id
    assert get_essay_feedback(
        user_id=user_id,
        essay_id=essay.id,
        session_factory=session_factory,
    ) == []
    assert (
        get_writing_remaining(user_id, session_factory=session_factory)
        == remaining_before
    )
    with session_factory() as session:
        assert session.scalar(select(func.count(WritingFeedback.id))) == 0
        assert session.scalar(select(func.count(AIUsageDaily.id))) == 0


def test_save_only_history_is_strictly_user_isolated(session_factory) -> None:
    """Another user cannot read a saved essay or its nonexistent feedback."""

    owner_id = _user_id(session_factory, "WritingSaveOwner")
    other_id = _user_id(session_factory, "WritingSaveOther")
    essay = save_essay_without_feedback(
        user_id=owner_id,
        test_type="General",
        task_type="Task 1",
        prompt="Write a letter about a community class.",
        content="Dear Manager,\n\nI am writing about the class.\n\nYours faithfully.",
        session_factory=session_factory,
    )

    assert get_essay_history(other_id, session_factory=session_factory) == []
    assert get_essay_feedback(
        user_id=other_id,
        essay_id=essay.id,
        session_factory=session_factory,
    ) == []


def test_mock_mode_page_saves_and_displays_essay_without_feedback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The normal no-key page path saves and reloads an owned essay."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="writing",
        username="WritingSavePage",
    )
    prompt = next(area for area in app.text_area if area.label == "作文题目")
    content = next(area for area in app.text_area if area.label == "作文正文")
    prompt.input("Discuss whether local parks should offer free classes.")
    content.input(
        "Free classes can support families and create stronger communities."
        "\n\nIn conclusion, local parks should provide a small weekly programme."
    ).run(timeout=10)

    next(button for button in app.button if button.label == "保存作文").click().run(
        timeout=10
    )
    assert any("不会生成AI评分" in item.value for item in app.warning)
    next(
        button for button in app.button if button.label == "确认保存作文"
    ).click().run(timeout=10)

    assert any(
        item.value == "作文已保存。AI评分当前未启用。"
        for item in app.success
    )
    user_id = app.session_state["user_id"]
    history = get_essay_history(user_id)
    assert len(history) == 1
    assert history[0].status == "saved"
    assert "Free classes can support families" in "\n".join(
        item.value for item in app.markdown
    )
    assert get_essay_feedback(user_id=user_id, essay_id=history[0].id) == []
