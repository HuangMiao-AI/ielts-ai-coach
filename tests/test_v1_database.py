"""Tests for the SQLAlchemy users schema and persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.connection import (
    create_database_engine,
    get_session_factory,
)
from ielts_ai_coach.database.models import (
    AIUsageDaily,
    Base,
    CoachMessage,
    Essay,
    PlanTask,
    ScoreRecord,
    StudentProfile,
    StudyLog,
    StudyPlan,
    TaskQuestionAttempt,
    User,
    WritingFeedback,
)


def test_users_table_has_required_columns(
    session_factory: sessionmaker[Session],
) -> None:
    """The users table must expose the approved V1 fields."""

    engine = session_factory.kw["bind"]
    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("users")}

    assert set(columns) == {
        "id",
        "username",
        "username_normalized",
        "password_hash",
        "is_active",
        "created_at",
    }
    assert columns["is_active"]["nullable"] is False


def test_public_model_module_exports_all_v1_models() -> None:
    """The stable model module must export every canonical V1 model name."""

    expected_tables = {
        User: "users",
        StudentProfile: "student_profiles",
        ScoreRecord: "score_records",
        StudyPlan: "study_plans",
        PlanTask: "plan_tasks",
        StudyLog: "study_logs",
        CoachMessage: "coach_messages",
        AIUsageDaily: "ai_usage_daily",
        Essay: "essays",
        WritingFeedback: "writing_feedback",
        TaskQuestionAttempt: "task_question_attempts",
    }

    assert {
        model.__name__: model.__tablename__
        for model in expected_tables
    } == {
        model.__name__: table_name
        for model, table_name in expected_tables.items()
    }


def test_task_question_attempt_table_is_additive_and_complete(
    session_factory: sessionmaker[Session],
) -> None:
    """The new table must preserve a complete scored review snapshot."""

    inspector = inspect(session_factory.kw["bind"])
    columns = {
        column["name"]
        for column in inspector.get_columns("task_question_attempts")
    }

    assert columns == {
        "id",
        "user_id",
        "task_id",
        "passage_id",
        "passage_version",
        "answers_json",
        "results_json",
        "score",
        "total_questions",
        "accuracy",
        "incorrect_question_ids_json",
        "submitted_at",
    }


def test_user_persists_after_database_reconnect(test_database_url: str) -> None:
    """A user must remain available after disposing and reopening SQLite."""

    first_engine = create_database_engine(test_database_url)
    Base.metadata.create_all(first_engine)
    first_factory = sessionmaker(
        bind=first_engine,
        class_=Session,
        expire_on_commit=False,
    )
    registered_user = register_user(
        "PersistentUser",
        "secure-pass-01",
        state={},
        session_factory=first_factory,
    )
    first_engine.dispose()

    second_engine = create_database_engine(test_database_url)
    second_factory = sessionmaker(bind=second_engine, class_=Session)
    with second_factory() as session:
        stored_user = session.scalar(
            select(User).where(User.id == registered_user.id)
        )

    assert stored_user is not None
    assert stored_user.username == "PersistentUser"
    second_engine.dispose()


def test_default_factory_tracks_database_url_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing DATABASE_URL must select a matching session factory."""

    first_url = f"sqlite:///{(tmp_path / 'first.db').as_posix()}"
    second_url = f"sqlite:///{(tmp_path / 'second.db').as_posix()}"

    monkeypatch.setenv("DATABASE_URL", first_url)
    first_factory = get_session_factory()
    monkeypatch.setenv("DATABASE_URL", second_url)
    second_factory = get_session_factory()

    assert first_factory.kw["bind"].url.database.endswith("first.db")
    assert second_factory.kw["bind"].url.database.endswith("second.db")
    assert first_factory is not second_factory
