"""Static privacy-boundary tests for exporter source records."""

from __future__ import annotations

from ielts_ai_coach.exporting.contracts import (
    FeedbackDetail,
    ReadingSourceRecord,
    WritingSourceRecord,
)
from ielts_ai_coach.exporting.privacy import (
    FORBIDDEN_FIELD_NAMES,
    assert_safe_field_names,
)


def test_source_contracts_contain_only_explicit_allowlist_fields() -> None:
    reading_fields = set(ReadingSourceRecord.model_fields)
    writing_fields = set(WritingSourceRecord.model_fields)
    detail_fields = set(FeedbackDetail.model_fields)

    assert reading_fields == {
        "source_record_id",
        "submitted_at",
        "passage_id",
        "passage_version",
        "score",
        "total_questions",
        "accuracy",
        "incorrect_question_ids",
        "details",
    }
    assert writing_fields == {
        "source_record_id",
        "created_at",
        "test_type",
        "task_type",
        "word_count",
        "task_response_or_achievement",
        "coherence_and_cohesion",
        "lexical_resource",
        "grammatical_range_and_accuracy",
        "estimated_overall",
        "strengths",
        "main_issues",
        "actionable_suggestions",
        "rewrite_example",
        "disclaimer",
        "provider",
        "model_name",
    }
    assert detail_fields == {
        "question_id",
        "question_type",
        "result",
        "explanation",
        "evidence",
    }
    assert not (
        (reading_fields | writing_fields | detail_fields)
        & FORBIDDEN_FIELD_NAMES
    )


def test_privacy_guard_rejects_sensitive_or_raw_fields() -> None:
    for forbidden in (
        "user_id",
        "username",
        "password_hash",
        "answers_json",
        "essay_content",
        "prompt",
        "raw_metadata",
        "last_error",
        "api_key",
        "token",
    ):
        try:
            assert_safe_field_names({"safe", forbidden})
        except ValueError as error:
            assert str(error) == "forbidden_export_field"
        else:
            raise AssertionError(f"{forbidden} was not rejected")
