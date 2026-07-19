"""Tests for deterministic reading feedback transformation."""

from __future__ import annotations

from datetime import datetime, timezone

from ielts_ai_coach.exporting.contracts import (
    FeedbackDetail,
    ReadingSourceRecord,
)
from ielts_ai_coach.exporting.enums import (
    FeedbackMethod,
    Skill,
    SourceEntity,
)
from ielts_ai_coach.exporting.transform import transform_reading


def _source(*, perfect: bool = False) -> ReadingSourceRecord:
    return ReadingSourceRecord(
        source_record_id=12,
        submitted_at=datetime(2026, 7, 18, 16, 30, tzinfo=timezone.utc),
        passage_id="academic-reading-1",
        passage_version="1.0",
        score=2 if perfect else 1,
        total_questions=2,
        accuracy=1.0 if perfect else 0.5,
        incorrect_question_ids=() if perfect else ("q1",),
        details=(
            FeedbackDetail(
                question_id="q1",
                question_type="Matching Heading",
                result="correct" if perfect else "incorrect",
                explanation="The paragraph focuses on the long-term effect.",
                evidence="The final sentence describes the effect.",
            ),
            FeedbackDetail(
                question_id="q2",
                question_type="Multiple Choice",
                result="correct",
                explanation="The second option matches the evidence.",
                evidence="The second paragraph states the reason.",
            ),
        ),
    )


def test_reading_transform_uses_shanghai_date_and_deterministic_rules() -> None:
    record = transform_reading(_source(), test=True)

    assert record.source_entity is SourceEntity.TASK_QUESTION_ATTEMPT
    assert record.source_record_id == 12
    assert record.session_date.isoformat() == "2026-07-19"
    assert record.generated_at.isoformat() == "2026-07-18T16:30:00+00:00"
    assert record.skill is Skill.READING
    assert record.feedback_method is FeedbackMethod.DETERMINISTIC
    assert record.provider is None
    assert record.model_name is None
    assert record.coach_version is None
    assert record.test is True
    assert "Score: 1/2" in record.overall_summary
    assert "Accuracy: 50.0%" in record.overall_summary
    assert record.weaknesses == ("Matching Heading: 1 incorrect",)
    assert any("main idea" in item for item in record.recommendations)


def test_reading_transform_handles_perfect_attempt_without_inventing_weakness() -> None:
    record = transform_reading(_source(perfect=True))

    assert record.weaknesses == ("No incorrect questions were detected.",)
    assert record.recommendations == (
        "Maintain this method and review again on schedule.",
    )


def test_reading_transform_contains_no_complete_answers() -> None:
    rendered = repr(transform_reading(_source()))

    assert "user_answer" not in rendered
    assert "correct_answer" not in rendered
    assert "answers_json" not in rendered
