"""Read-only, user-scoped source queries for exporter V1."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.models import (
    Essay,
    StudentProfile,
    TaskQuestionAttempt,
    User,
    WritingFeedback,
)
from ielts_ai_coach.exporting.contracts import (
    ExportUserSummary,
    FeedbackDetail,
    ReadingSourceRecord,
    WritingSourceRecord,
)
from ielts_ai_coach.exporting.errors import ExportDatabaseError


def _aware_utc(value: datetime) -> datetime:
    """Treat SQLite's naive stored timestamps as application UTC."""

    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _safe_limit(limit: int | None) -> int | None:
    """Validate a bounded optional source limit."""

    if limit is None:
        return None
    if limit < 1:
        raise ValueError("invalid_limit")
    return min(limit, 1000)


def _load_json_list(payload: str, *, error_code: str) -> list[object]:
    """Load one internal JSON list without returning its original string."""

    try:
        value = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as error:
        raise ExportDatabaseError(error_code) from error
    if not isinstance(value, list):
        raise ExportDatabaseError(error_code)
    return value


def _reading_details(payload: str) -> tuple[FeedbackDetail, ...]:
    """Select only approved fields from the persisted result snapshot."""

    try:
        document = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as error:
        raise ExportDatabaseError("invalid_reading_results") from error
    if not isinstance(document, dict) or not isinstance(
        document.get("results"), list
    ):
        raise ExportDatabaseError("invalid_reading_results")
    details = []
    for item in document["results"]:
        if not isinstance(item, dict):
            raise ExportDatabaseError("invalid_reading_results")
        try:
            details.append(
                FeedbackDetail(
                    question_id=str(item["question_id"]),
                    question_type=str(item["question_type"]),
                    result=(
                        "correct"
                        if item.get("is_correct") is True
                        else "incorrect"
                    ),
                    explanation=str(item.get("explanation", "")),
                    evidence=str(item.get("evidence", "")),
                )
            )
        except (KeyError, ValueError) as error:
            raise ExportDatabaseError("invalid_reading_results") from error
    return tuple(details)


def list_exportable_reading_attempts(
    session: Session,
    *,
    user_id: int,
    after_id: int = 0,
    limit: int | None = None,
) -> list[ReadingSourceRecord]:
    """Return allowlisted reading attempts for exactly one user."""

    if user_id < 1 or after_id < 0:
        raise ValueError("invalid_source_scope")
    statement = (
        select(
            TaskQuestionAttempt.id,
            TaskQuestionAttempt.submitted_at,
            TaskQuestionAttempt.passage_id,
            TaskQuestionAttempt.passage_version,
            TaskQuestionAttempt.score,
            TaskQuestionAttempt.total_questions,
            TaskQuestionAttempt.accuracy,
            TaskQuestionAttempt.incorrect_question_ids_json,
            TaskQuestionAttempt.results_json,
        )
        .where(
            TaskQuestionAttempt.user_id == user_id,
            TaskQuestionAttempt.id > after_id,
        )
        .order_by(TaskQuestionAttempt.id)
    )
    safe_limit = _safe_limit(limit)
    if safe_limit is not None:
        statement = statement.limit(safe_limit)
    records = []
    for row in session.execute(statement):
        incorrect = tuple(
            str(item)
            for item in _load_json_list(
                row.incorrect_question_ids_json,
                error_code="invalid_incorrect_question_ids",
            )
        )
        records.append(
            ReadingSourceRecord(
                source_record_id=row.id,
                submitted_at=_aware_utc(row.submitted_at),
                passage_id=row.passage_id,
                passage_version=row.passage_version,
                score=row.score,
                total_questions=row.total_questions,
                accuracy=row.accuracy,
                incorrect_question_ids=incorrect,
                details=_reading_details(row.results_json),
            )
        )
    return records


def list_exportable_writing_feedback(
    session: Session,
    *,
    user_id: int,
    after_id: int = 0,
    limit: int | None = None,
) -> list[WritingSourceRecord]:
    """Return allowlisted writing feedback for exactly one user."""

    if user_id < 1 or after_id < 0:
        raise ValueError("invalid_source_scope")
    statement = (
        select(
            WritingFeedback.id,
            WritingFeedback.created_at,
            Essay.test_type,
            Essay.task_type,
            Essay.word_count,
            WritingFeedback.task_response_or_achievement,
            WritingFeedback.coherence_and_cohesion,
            WritingFeedback.lexical_resource,
            WritingFeedback.grammatical_range_and_accuracy,
            WritingFeedback.estimated_overall,
            WritingFeedback.strengths,
            WritingFeedback.main_issues,
            WritingFeedback.actionable_suggestions,
            WritingFeedback.rewrite_example,
            WritingFeedback.disclaimer,
            WritingFeedback.provider,
            WritingFeedback.model_name,
        )
        .join(Essay, Essay.id == WritingFeedback.essay_id)
        .where(
            WritingFeedback.user_id == user_id,
            Essay.user_id == user_id,
            WritingFeedback.id > after_id,
        )
        .order_by(WritingFeedback.id)
    )
    safe_limit = _safe_limit(limit)
    if safe_limit is not None:
        statement = statement.limit(safe_limit)
    return [
        WritingSourceRecord(
            source_record_id=row.id,
            created_at=_aware_utc(row.created_at),
            test_type=row.test_type,
            task_type=row.task_type,
            word_count=row.word_count,
            task_response_or_achievement=row.task_response_or_achievement,
            coherence_and_cohesion=row.coherence_and_cohesion,
            lexical_resource=row.lexical_resource,
            grammatical_range_and_accuracy=(
                row.grammatical_range_and_accuracy
            ),
            estimated_overall=row.estimated_overall,
            strengths=tuple(str(item) for item in row.strengths),
            main_issues=tuple(str(item) for item in row.main_issues),
            actionable_suggestions=tuple(
                str(item) for item in row.actionable_suggestions
            ),
            rewrite_example=row.rewrite_example,
            disclaimer=row.disclaimer,
            provider=row.provider,
            model_name=row.model_name,
        )
        for row in session.execute(statement)
    ]


def list_export_users(session: Session) -> list[ExportUserSummary]:
    """Return minimum non-sensitive information for explicit user selection."""

    users = session.execute(select(User.id, User.username).order_by(User.id))
    summaries = []
    for user_id, username in users:
        has_profile = bool(
            session.scalar(
                select(func.count(StudentProfile.id)).where(
                    StudentProfile.user_id == user_id
                )
            )
        )
        reading_count = int(
            session.scalar(
                select(func.count(TaskQuestionAttempt.id)).where(
                    TaskQuestionAttempt.user_id == user_id
                )
            )
            or 0
        )
        writing_count = int(
            session.scalar(
                select(func.count(WritingFeedback.id)).where(
                    WritingFeedback.user_id == user_id
                )
            )
            or 0
        )
        latest_reading = session.scalar(
            select(func.max(TaskQuestionAttempt.submitted_at)).where(
                TaskQuestionAttempt.user_id == user_id
            )
        )
        latest_writing = session.scalar(
            select(func.max(WritingFeedback.created_at)).where(
                WritingFeedback.user_id == user_id
            )
        )
        recent_values = [
            _aware_utc(item)
            for item in (latest_reading, latest_writing)
            if item is not None
        ]
        summaries.append(
            ExportUserSummary(
                user_id=user_id,
                account_label=username,
                has_profile=has_profile,
                reading_count=reading_count,
                writing_count=writing_count,
                recent_activity_at=max(recent_values)
                if recent_values
                else None,
            )
        )
    return summaries


def create_read_only_session_factory(
    database_path: Path,
) -> sessionmaker[Session]:
    """Create a query-only SQLite session factory without WAL mutation."""

    resolved = database_path.expanduser().resolve()
    if not resolved.is_file():
        raise ExportDatabaseError("database_missing")
    encoded_path = quote(resolved.as_posix(), safe="/:")
    engine = create_engine(
        f"sqlite+pysqlite:///file:{encoded_path}?mode=ro&uri=true",
        connect_args={"check_same_thread": False, "timeout": 5},
        pool_pre_ping=True,
    )

    @event.listens_for(engine, "connect")
    def configure_read_only(connection: object, _: object) -> None:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA query_only=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )
