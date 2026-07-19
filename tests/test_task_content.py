"""Tests for deterministic concrete task content and legacy compatibility."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from types import SimpleNamespace

from ielts_ai_coach.ai.factory import get_ai_provider
from ielts_ai_coach.services.planning_rules import build_plan_blueprint
from ielts_ai_coach.services.task_content import (
    TASK_CONTENT_PREFIX,
    get_task_content,
)
from ielts_ai_coach.services.task_templates import build_task_content


def _concrete_blueprint():
    """Build a plan containing all four IELTS subjects every day."""

    today = date(2026, 7, 16)
    return build_plan_blueprint(
        scores={
            "listening": 6.0,
            "reading": 6.0,
            "writing": 6.0,
            "speaking": 6.0,
        },
        target_overall=7.0,
        exam_date=today + timedelta(days=60),
        daily_minutes=160,
        start_date=today,
    )


def test_every_generated_task_has_executable_content() -> None:
    """New tasks must contain all approved student-facing content fields."""

    blueprint = _concrete_blueprint()
    for task in blueprint.tasks:
        assert task.task_title
        assert task.objective
        assert task.material
        assert 3 <= len(task.instructions) <= 5
        assert task.completion_criteria
        assert task.expected_output
        assert task.difficulty
        assert task.description.startswith(TASK_CONTENT_PREFIX)


def test_mock_mode_plan_is_specific_and_preserves_minutes(
    monkeypatch,
) -> None:
    """Concrete deterministic tasks must not depend on a configured Qwen key."""

    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    assert get_ai_provider().is_mock

    blueprint = _concrete_blueprint()
    minutes_by_date: dict[date, int] = defaultdict(int)
    subjects = set()
    for task in blueprint.tasks:
        minutes_by_date[task.task_date] += task.planned_minutes
        subjects.add(task.subject)
    assert set(minutes_by_date.values()) == {160}
    assert subjects == {"listening", "reading", "writing", "speaking"}
    assert all("专项训练" not in task.task_title for task in blueprint.tasks)


def test_subject_templates_include_required_original_or_owned_material() -> None:
    """Each subject must carry the V1-specific material contract."""

    tasks = {task.subject: task for task in _concrete_blueprint().tasks[:4]}
    listening = get_task_content(
        SimpleNamespace(
            title=tasks["listening"].task_title,
            description=tasks["listening"].description,
            subject="listening",
            task_type=tasks["listening"].task_type,
            planned_minutes=tasks["listening"].planned_minutes,
        )
    )
    reading = get_task_content(
        SimpleNamespace(
            title=tasks["reading"].task_title,
            description=tasks["reading"].description,
            subject="reading",
            task_type=tasks["reading"].task_type,
            planned_minutes=tasks["reading"].planned_minutes,
        )
    )
    writing = get_task_content(
        SimpleNamespace(
            title=tasks["writing"].task_title,
            description=tasks["writing"].description,
            subject="writing",
            task_type=tasks["writing"].task_type,
            planned_minutes=tasks["writing"].planned_minutes,
        )
    )
    speaking = get_task_content(
        SimpleNamespace(
            title=tasks["speaking"].task_title,
            description=tasks["speaking"].description,
            subject="speaking",
            task_type=tasks["speaking"].task_type,
            planned_minutes=tasks["speaking"].planned_minutes,
        )
    )

    assert "合法拥有" in listening.material
    assert "不附带真题音频" in listening.material
    assert reading.reading_passage_id.startswith("AR-V1-")
    assert reading.reading_passage_version == "1.0.0"
    assert "项目原创" in reading.material
    assert writing.writing_prompt and writing.writing_test_type
    assert speaking.questions
    assert "不进行自动语音评分" in " ".join(speaking.instructions)


def test_new_reading_tasks_rotate_into_v2_with_dynamic_question_copy() -> None:
    """Later plan days must use the additive catalog and accurate question count."""

    reading = build_task_content(
        subject="reading",
        phase="targeted",
        day_offset=4,
        planned_minutes=35,
    )

    assert reading.reading_passage_id == "AR-V2-002"
    assert reading.reading_passage_version == "2.0.0"
    assert "10道题" in " ".join(reading.instructions)
    assert "全部10题" in reading.completion_criteria


def test_old_plain_text_task_stays_readable() -> None:
    """A pre-refactor task must receive a safe read-time fallback."""

    old_task = SimpleNamespace(
        title="写作·专项训练",
        description="审题、提纲、段落写作与四项自查。",
        subject="writing",
        task_type="专项训练",
        planned_minutes=37,
    )

    content = get_task_content(old_task)

    assert content.task_title == old_task.title
    assert content.template_id == "legacy-task"
    assert content.planned_minutes == 37
    assert len(content.instructions) == 3
    assert "旧计划未保存具体材料" in content.material
