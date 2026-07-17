"""Tests for deterministic IELTS scoring and user-owned history."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.services.scoring import (
    ScoreValidationError,
    analyze_scores,
    calculate_overall,
)
from ielts_ai_coach.services.scores import (
    get_latest_score,
    list_score_history,
    save_score_record,
)


def _create_user(
    username: str, session_factory: sessionmaker[Session]
) -> int:
    """Create a test user and return its ID."""

    return register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id


def test_overall_and_tied_weaknesses_are_deterministic() -> None:
    """Overall rounding and tied minimum detection must not use AI."""

    scores = {
        "listening": 6.5,
        "reading": 6.5,
        "writing": 5.5,
        "speaking": 5.5,
    }
    diagnosis = analyze_scores(scores, target_overall=7.0)

    assert calculate_overall(scores) == 6.0
    assert diagnosis.lowest_subjects == ("writing", "speaking")
    assert diagnosis.overall_gap == 1.0
    assert diagnosis.subject_gaps["writing"] == 1.5


def test_quarter_band_input_is_rejected() -> None:
    """Section scores must use valid half-band increments."""

    with pytest.raises(ScoreValidationError):
        calculate_overall(
            {
                "listening": 6.25,
                "reading": 6.0,
                "writing": 6.0,
                "speaking": 6.0,
            }
        )


def test_multiple_score_records_keep_newest_first(
    session_factory: sessionmaker[Session],
) -> None:
    """A user must retain multiple scores ordered from newest to oldest."""

    user_id = _create_user("ScoreHistory", session_factory)
    base_time = datetime(2026, 7, 1, tzinfo=timezone.utc)
    first_scores = {
        "listening": 5.5,
        "reading": 6.0,
        "writing": 5.0,
        "speaking": 5.5,
    }
    second_scores = {
        "listening": 6.5,
        "reading": 6.5,
        "writing": 5.5,
        "speaking": 6.0,
    }
    save_score_record(
        user_id=user_id,
        scores=first_scores,
        recorded_at=base_time,
        session_factory=session_factory,
    )
    save_score_record(
        user_id=user_id,
        scores=second_scores,
        recorded_at=base_time + timedelta(days=7),
        session_factory=session_factory,
    )

    history = list_score_history(user_id, session_factory=session_factory)
    latest = get_latest_score(user_id, session_factory=session_factory)

    assert len(history) == 2
    assert history[0].listening == 6.5
    assert latest.id == history[0].id


def test_score_history_is_isolated_by_user(
    session_factory: sessionmaker[Session],
) -> None:
    """One user cannot list another user's score records."""

    first_user_id = _create_user("ScoreOne", session_factory)
    second_user_id = _create_user("ScoreTwo", session_factory)
    scores = {
        "listening": 6.0,
        "reading": 6.0,
        "writing": 5.5,
        "speaking": 5.5,
    }
    save_score_record(
        user_id=first_user_id,
        scores=scores,
        session_factory=session_factory,
    )

    assert len(
        list_score_history(first_user_id, session_factory=session_factory)
    ) == 1
    assert (
        list_score_history(second_user_id, session_factory=session_factory) == []
    )
