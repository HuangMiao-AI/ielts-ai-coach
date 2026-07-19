"""Explicit source-to-contract transformations for exporter V1."""

from __future__ import annotations

from collections import Counter
from zoneinfo import ZoneInfo

from ielts_ai_coach.exporting.contracts import (
    FeedbackExportRecord,
    ReadingSourceRecord,
    WritingSourceRecord,
)
from ielts_ai_coach.exporting.enums import (
    FeedbackMethod,
    FeedbackStatus,
    Skill,
    SourceEntity,
)


DEFAULT_TIMEZONE = "Asia/Shanghai"
READING_RECOMMENDATIONS = {
    "Matching Heading": (
        "Summarize each paragraph's main idea before matching headings."
    ),
    "Multiple Choice": (
        "Locate the evidence first, then compare every distractor."
    ),
    "True/False/Not Given": (
        "Separate a contradicted statement from information that is not stated."
    ),
}
FALLBACK_RECOMMENDATION = (
    "Review the saved explanation and evidence for each incorrect question."
)


def transform_reading(
    source: ReadingSourceRecord,
    *,
    timezone_name: str = DEFAULT_TIMEZONE,
    test: bool = False,
) -> FeedbackExportRecord:
    """Build deterministic reading feedback without AI or raw answers."""

    session_date = source.submitted_at.astimezone(
        ZoneInfo(timezone_name)
    ).date()
    incorrect_details = [
        detail for detail in source.details if detail.result == "incorrect"
    ]
    counts = Counter(detail.question_type for detail in incorrect_details)
    if counts:
        weaknesses = tuple(
            f"{question_type}: {count} incorrect"
            for question_type, count in sorted(counts.items())
        )
        recommendations = tuple(
            READING_RECOMMENDATIONS.get(
                question_type, FALLBACK_RECOMMENDATION
            )
            for question_type in sorted(counts)
        )
    else:
        weaknesses = ("No incorrect questions were detected.",)
        recommendations = (
            "Maintain this method and review again on schedule.",
        )
    return FeedbackExportRecord(
        source_entity=SourceEntity.TASK_QUESTION_ATTEMPT,
        source_record_id=source.source_record_id,
        session_date=session_date,
        generated_at=source.submitted_at,
        coach_version=None,
        skill=Skill.READING,
        feedback_method=FeedbackMethod.DETERMINISTIC,
        provider=None,
        model_name=None,
        feedback_status=FeedbackStatus.GENERATED,
        overall_summary=(
            f"Score: {source.score}/{source.total_questions}",
            f"Accuracy: {source.accuracy:.1%}",
            f"Passage ID: {source.passage_id}",
            f"Passage Version: {source.passage_version}",
        ),
        weaknesses=weaknesses,
        recommendations=recommendations,
        detailed_feedback=source.details,
        test=test,
    )


def transform_writing(
    source: WritingSourceRecord,
    *,
    timezone_name: str = DEFAULT_TIMEZONE,
    test: bool = False,
) -> FeedbackExportRecord:
    """Build writing feedback without loading or exporting the essay."""

    session_date = source.created_at.astimezone(
        ZoneInfo(timezone_name)
    ).date()
    return FeedbackExportRecord(
        source_entity=SourceEntity.WRITING_FEEDBACK,
        source_record_id=source.source_record_id,
        session_date=session_date,
        generated_at=source.created_at,
        coach_version=None,
        skill=Skill.WRITING,
        feedback_method=FeedbackMethod.AI,
        provider=source.provider or None,
        model_name=source.model_name or None,
        feedback_status=FeedbackStatus.GENERATED,
        overall_summary=(
            f"Estimated Overall: {source.estimated_overall:.1f}",
            (
                "Task Response/Achievement: "
                f"{source.task_response_or_achievement:.1f}"
            ),
            f"Coherence and Cohesion: {source.coherence_and_cohesion:.1f}",
            f"Lexical Resource: {source.lexical_resource:.1f}",
            (
                "Grammatical Range and Accuracy: "
                f"{source.grammatical_range_and_accuracy:.1f}"
            ),
            f"Test Type: {source.test_type}",
            f"Task Type: {source.task_type}",
            f"Word Count: {source.word_count}",
            f"Disclaimer: {source.disclaimer}",
        ),
        strengths=source.strengths,
        weaknesses=source.main_issues,
        recommendations=source.actionable_suggestions,
        rewrite_example=source.rewrite_example,
        disclaimer=source.disclaimer,
        test=test,
    )
