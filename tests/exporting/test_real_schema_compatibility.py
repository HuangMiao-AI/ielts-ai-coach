"""Schema compatibility tests for exporter source columns."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.orm import Session, sessionmaker


def test_export_sources_match_the_active_v1_schema(
    session_factory: sessionmaker[Session],
) -> None:
    inspector = inspect(session_factory.kw["bind"])

    attempt_columns = {
        item["name"]
        for item in inspector.get_columns("task_question_attempts")
    }
    feedback_columns = {
        item["name"] for item in inspector.get_columns("writing_feedback")
    }
    essay_columns = {item["name"] for item in inspector.get_columns("essays")}

    assert {
        "id",
        "user_id",
        "submitted_at",
        "passage_id",
        "passage_version",
        "score",
        "total_questions",
        "accuracy",
        "incorrect_question_ids_json",
        "results_json",
    } <= attempt_columns
    assert {
        "id",
        "user_id",
        "essay_id",
        "created_at",
        "estimated_overall",
        "strengths",
        "main_issues",
        "actionable_suggestions",
        "rewrite_example",
        "disclaimer",
        "provider",
        "model_name",
    } <= feedback_columns
    assert {
        "id",
        "user_id",
        "test_type",
        "task_type",
        "word_count",
    } <= essay_columns
