"""Persistence orchestration for validated IELTS score records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.account_repository import (
    create_score_record,
    get_latest_score as repository_get_latest_score,
    list_score_records as repository_list_score_records,
)
from ielts_ai_coach.database.connection import get_session_factory, session_scope
from ielts_ai_coach.database.models import ScoreRecord
from ielts_ai_coach.services.scoring import calculate_overall, validate_scores


MAX_SCORE_NOTE_LENGTH = 300


class ScoreRecordValidationError(ValueError):
    """Raised when score-record metadata is invalid."""


def save_score_record(
    *,
    user_id: int,
    scores: dict[str, float],
    note: str = "",
    recorded_at: datetime | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> ScoreRecord:
    """Validate and save one score record owned by a user."""

    validate_scores(scores)
    cleaned_note = note.strip()
    if len(cleaned_note) > MAX_SCORE_NOTE_LENGTH:
        raise ScoreRecordValidationError("note_too_long")

    factory = session_factory or get_session_factory()
    with session_scope(factory) as session:
        return create_score_record(
            session,
            user_id=user_id,
            listening=float(scores["listening"]),
            reading=float(scores["reading"]),
            writing=float(scores["writing"]),
            speaking=float(scores["speaking"]),
            overall=calculate_overall(scores),
            note=cleaned_note,
            recorded_at=recorded_at,
        )


def list_score_history(
    user_id: int,
    *,
    limit: int = 100,
    session_factory: sessionmaker[Session] | None = None,
) -> list[ScoreRecord]:
    """Return score history owned by a user."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        return repository_list_score_records(
            session, user_id=user_id, limit=limit
        )


def get_latest_score(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> ScoreRecord | None:
    """Return the newest score owned by a user."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        return repository_get_latest_score(session, user_id)
