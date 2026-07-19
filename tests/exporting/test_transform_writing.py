"""Tests for allowlisted writing feedback transformation."""

from __future__ import annotations

from datetime import datetime, timezone

from ielts_ai_coach.exporting.contracts import WritingSourceRecord
from ielts_ai_coach.exporting.enums import (
    FeedbackMethod,
    Skill,
    SourceEntity,
)
from ielts_ai_coach.exporting.transform import transform_writing


def _source() -> WritingSourceRecord:
    return WritingSourceRecord(
        source_record_id=31,
        created_at=datetime(2026, 7, 19, 2, 30, tzinfo=timezone.utc),
        test_type="Academic",
        task_type="Task 2",
        word_count=278,
        task_response_or_achievement=6.0,
        coherence_and_cohesion=6.5,
        lexical_resource=6.0,
        grammatical_range_and_accuracy=5.5,
        estimated_overall=6.0,
        strengths=("Clear position", "Relevant example"),
        main_issues=("Sentence control",),
        actionable_suggestions=("Use shorter complex sentences.",),
        rewrite_example="A clearer paragraph with controlled sentence structure.",
        disclaimer="This is an AI estimate, not an official IELTS score.",
        provider="qwen",
        model_name="qwen-plus",
    )


def test_writing_transform_maps_only_structured_feedback() -> None:
    record = transform_writing(_source(), test=True)

    assert record.source_entity is SourceEntity.WRITING_FEEDBACK
    assert record.source_record_id == 31
    assert record.session_date.isoformat() == "2026-07-19"
    assert record.skill is Skill.WRITING
    assert record.feedback_method is FeedbackMethod.AI
    assert record.provider == "qwen"
    assert record.model_name == "qwen-plus"
    assert record.coach_version is None
    assert record.strengths == ("Clear position", "Relevant example")
    assert record.weaknesses == ("Sentence control",)
    assert record.recommendations == ("Use shorter complex sentences.",)
    assert "Estimated Overall: 6.0" in record.overall_summary
    assert "Word Count: 278" in record.overall_summary
    assert record.test is True


def test_writing_transform_does_not_expose_essay_or_prompt_fields() -> None:
    record_text = repr(transform_writing(_source()))

    assert "essay_content" not in record_text
    assert "prompt" not in record_text
    assert "raw_metadata" not in record_text
    assert "last_error" not in record_text
