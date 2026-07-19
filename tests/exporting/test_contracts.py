"""Contract tests for versioned exporter records."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from ielts_ai_coach.exporting.contracts import (
    FeedbackDetail,
    FeedbackExportRecord,
)
from ielts_ai_coach.exporting.enums import (
    FeedbackMethod,
    FeedbackStatus,
    Skill,
    SourceEntity,
)


def _record(**overrides: object) -> FeedbackExportRecord:
    values: dict[str, object] = {
        "source_entity": SourceEntity.TASK_QUESTION_ATTEMPT,
        "source_record_id": 7,
        "session_date": date(2026, 7, 19),
        "generated_at": datetime(2026, 7, 19, 2, 30, tzinfo=timezone.utc),
        "skill": Skill.READING,
        "feedback_method": FeedbackMethod.DETERMINISTIC,
        "feedback_status": FeedbackStatus.GENERATED,
        "overall_summary": ("Score: 8/9",),
        "weaknesses": ("Matching Heading: 1 incorrect",),
        "recommendations": ("Review the saved explanation.",),
        "detailed_feedback": (
            FeedbackDetail(
                question_id="r1-q2",
                question_type="Matching Heading",
                result="incorrect",
                explanation="The paragraph focuses on the later effect.",
                evidence="The final sentence states the effect.",
            ),
        ),
        "test": True,
    }
    values.update(overrides)
    return FeedbackExportRecord.model_validate(values)


def test_feedback_record_freezes_fixed_contract_values() -> None:
    record = _record()

    assert record.schema_version == 1
    assert record.type == "ai-coach-feedback"
    assert record.source_system == "ielts-ai-coach"
    assert record.exporter_version == "1.0.0"
    assert record.source_record_id == 7
    assert record.test is True
    assert record.tags == ("ielts", "ai-coach-feedback")


def test_feedback_record_rejects_extra_fields_and_naive_timestamps() -> None:
    with pytest.raises(ValidationError):
        _record(password_hash="forbidden")

    with pytest.raises(ValidationError, match="timezone"):
        _record(generated_at=datetime(2026, 7, 19, 2, 30))


def test_source_id_must_be_positive_integer() -> None:
    with pytest.raises(ValidationError):
        _record(source_record_id=0)

    with pytest.raises(ValidationError):
        _record(source_record_id="7")


def test_export_enums_are_stable() -> None:
    assert {item.value for item in SourceEntity} == {
        "task_question_attempt",
        "writing_feedback",
    }
    assert {item.value for item in Skill} == {"reading", "writing"}
    assert {item.value for item in FeedbackMethod} == {
        "deterministic",
        "ai",
    }
    assert {item.value for item in FeedbackStatus} == {
        "generated",
        "reviewed",
        "superseded",
    }
