"""Tests for the versioned project-original academic reading bank."""

from __future__ import annotations

from types import SimpleNamespace

from ielts_ai_coach.services.question_bank import (
    BANK_PATH,
    VALID_QUESTION_TYPES,
    get_reading_bank,
)
from ielts_ai_coach.services.reading_practice import resolve_reading_passage
from ielts_ai_coach.services.task_content import (
    TaskContent,
    serialize_task_content,
)


def test_reading_bank_loads_three_complete_original_passages() -> None:
    """V1 must provide three validated 800–1000 word academic passages."""

    bank = get_reading_bank()

    assert bank.version == "1.0.0"
    assert len(bank.passages) == 3
    for passage in bank.passages:
        assert 800 <= passage.word_count <= 1000
        assert len(passage.questions) == 9
        assert {
            question.question_type for question in passage.questions
        } == VALID_QUESTION_TYPES
        assert passage.source_type == "project_original"
        assert passage.is_official_ielts_content is False
        for question in passage.questions:
            assert question.question
            assert len(question.options) >= 3
            assert question.correct_answer in question.options
            assert question.explanation
            assert question.evidence


def test_reading_bank_has_unique_ids_and_no_protected_test_source() -> None:
    """Bundled content must use unique IDs and contain no copied-test source."""

    bank = get_reading_bank()
    passage_ids = [passage.passage_id for passage in bank.passages]
    question_ids = [
        question.question_id
        for passage in bank.passages
        for question in passage.questions
    ]
    raw_source = BANK_PATH.read_text(encoding="utf-8").casefold()

    assert len(set(passage_ids)) == len(passage_ids)
    assert len(set(question_ids)) == len(question_ids)
    assert "cambridge" not in raw_source
    assert '"source_type": "project_original"' in raw_source
    assert '"is_official_ielts_content": false' in raw_source


def test_existing_structured_reading_task_gets_compatible_practice() -> None:
    """A stored task-content-v1 row can gain a passage without being rewritten."""

    content = TaskContent(
        task_title="旧阅读任务",
        objective="完成阅读",
        material="旧原创材料",
        instructions=("步骤一", "步骤二", "步骤三"),
        completion_criteria="完成",
        planned_minutes=30,
        subject="reading",
        difficulty="进阶",
        expected_output="答案",
        template_id="R-V1-001",
    )
    task = SimpleNamespace(
        id=2,
        title=content.task_title,
        description=serialize_task_content(content),
        subject="reading",
        task_type="专项训练",
        planned_minutes=30,
    )

    passage = resolve_reading_passage(task)

    assert passage is not None
    assert passage.passage_id == "AR-V1-002"
