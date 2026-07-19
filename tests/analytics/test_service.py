"""Behavior tests for read-only user-scoped learning analytics."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.writing_repository import (
    list_user_writing_feedback,
)
from ielts_ai_coach.services.analytics import build_analytics_result
from tests.analytics.helpers import (
    add_profile,
    add_reading_attempt,
    add_score,
    add_study_log,
    add_writing_feedback,
    create_user,
    reading_snapshot,
)


TODAY = date(2026, 7, 19)


def _seed_owner_data(
    session_factory: sessionmaker[Session],
) -> tuple[int, int]:
    """Seed distinct owner and other-user evidence for aggregation tests."""

    owner_id = create_user("AnalyticsOwner", session_factory)
    other_id = create_user("AnalyticsOther", session_factory)
    with session_factory.begin() as session:
        add_profile(session, user_id=owner_id)
        add_score(
            session,
            user_id=owner_id,
            overall=5.5,
            listening=6.0,
            reading=5.0,
            writing=5.5,
            speaking=5.0,
            recorded_at=datetime(2026, 7, 1, 9, 0),
        )
        add_score(
            session,
            user_id=owner_id,
            overall=6.0,
            listening=6.5,
            reading=6.0,
            writing=6.0,
            speaking=5.5,
            recorded_at=datetime(2026, 7, 15, 9, 0),
        )
        add_reading_attempt(
            session,
            user_id=owner_id,
            score=3,
            total_questions=5,
            results_json=reading_snapshot(
                [
                    ("true_false_not_given", True),
                    ("true_false_not_given", True),
                    ("true_false_not_given", True),
                    ("true_false_not_given", False),
                    ("true_false_not_given", False),
                ]
            ),
            submitted_at=datetime(2026, 7, 10, 9, 0),
        )
        add_reading_attempt(
            session,
            user_id=owner_id,
            score=6,
            total_questions=10,
            results_json=reading_snapshot(
                [
                    *(("multiple_choice", True),) * 6,
                    *(("matching_heading", False),) * 3,
                    ("multiple_choice", False),
                ]
            ),
            submitted_at=datetime(2026, 7, 12, 9, 0),
        )
        add_reading_attempt(
            session,
            user_id=owner_id,
            score=3,
            total_questions=5,
            results_json="not valid JSON",
            submitted_at=datetime(2026, 7, 14, 9, 0),
        )
        add_writing_feedback(
            session,
            user_id=owner_id,
            task_response=5.0,
            coherence=5.0,
            vocabulary=5.5,
            grammar=5.0,
            created_at=datetime(2026, 7, 5, 9, 0),
        )
        add_writing_feedback(
            session,
            user_id=owner_id,
            task_response=6.0,
            coherence=5.5,
            vocabulary=6.0,
            grammar=5.5,
            created_at=datetime(2026, 7, 16, 9, 0),
        )
        add_study_log(
            session, user_id=owner_id, study_date=TODAY, minutes=30
        )
        add_study_log(
            session,
            user_id=owner_id,
            study_date=TODAY - timedelta(days=1),
            minutes=45,
        )
        add_study_log(
            session,
            user_id=owner_id,
            study_date=TODAY - timedelta(days=3),
            minutes=15,
        )
        add_study_log(
            session,
            user_id=owner_id,
            study_date=TODAY - timedelta(days=90),
            minutes=100,
        )
        add_profile(session, user_id=other_id, target_overall=9.0)
        add_score(
            session,
            user_id=other_id,
            overall=9.0,
            listening=9.0,
            reading=9.0,
            writing=9.0,
            speaking=9.0,
            recorded_at=datetime(2026, 7, 18, 9, 0),
        )
        add_writing_feedback(
            session,
            user_id=other_id,
            task_response=9.0,
            coherence=9.0,
            vocabulary=9.0,
            grammar=9.0,
            created_at=datetime(2026, 7, 18, 9, 0),
        )
        add_study_log(
            session, user_id=other_id, study_date=TODAY, minutes=240
        )
    return owner_id, other_id


def test_builds_evidence_backed_analytics_for_only_the_requested_user(
    session_factory: sessionmaker[Session],
) -> None:
    """Analytics must aggregate owned scores, practice, feedback, and logs."""

    owner_id, _ = _seed_owner_data(session_factory)

    result = build_analytics_result(
        owner_id, today=TODAY, session_factory=session_factory
    )

    assert result.current_band == 6.0
    assert result.target_band == 7.0
    assert result.target_gap == 1.0
    assert [point.band for point in result.overall_trend] == [5.5, 6.0]
    assert result.skill("listening").latest_band == 6.5
    assert [point.band for point in result.skill("listening").trend] == [
        6.0,
        6.5,
    ]
    assert result.skill("speaking").latest_band == 5.5
    assert [point.band for point in result.skill("speaking").trend] == [
        5.0,
        5.5,
    ]
    assert result.skill("speaking").detail_status == (
        "No detailed practice analytics available"
    )
    assert result.reading.attempt_count == 3
    assert result.reading.correct == 12
    assert result.reading.total == 20
    assert result.reading.accuracy == pytest.approx(0.6)
    assert dict(result.reading.error_counts) == {
        "matching_heading": 3,
        "true_false_not_given": 2,
        "multiple_choice": 1,
    }
    assert result.reading.frequent_error_types == ("matching_heading",)
    assert result.reading.warnings == ("invalid_reading_snapshot",)
    assert result.writing.feedback_count == 2
    assert result.writing.dimension("grammar").latest_band == 5.5
    assert [
        point.band for point in result.writing.dimension("grammar").trend
    ] == [5.0, 5.5]
    assert result.behavior.streak_days == 2
    assert result.behavior.recent_minutes == 90
    assert result.behavior.daily_study_minutes == 60


def test_analytics_isolated_from_other_users_and_rejects_unknown_names(
    session_factory: sessionmaker[Session],
) -> None:
    """Other users' records must not affect aggregates or lookup contracts."""

    owner_id, other_id = _seed_owner_data(session_factory)

    result = build_analytics_result(
        owner_id, today=TODAY, session_factory=session_factory
    )
    with session_factory() as session:
        other_feedback = list_user_writing_feedback(
            session, user_id=other_id
        )

    assert [point.band for point in result.overall_trend] == [5.5, 6.0]
    assert result.writing.feedback_count == 2
    assert result.behavior.recent_minutes == 90
    assert len(other_feedback) == 1
    assert other_feedback[0].user_id == other_id
    with pytest.raises(KeyError):
        result.skill("unknown")
    with pytest.raises(KeyError):
        result.writing.dimension("unknown")


def test_empty_user_has_only_factual_absent_evidence(
    session_factory: sessionmaker[Session],
) -> None:
    """A user without records must not receive fabricated performance values."""

    user_id = create_user("AnalyticsEmpty", session_factory)

    result = build_analytics_result(
        user_id, today=TODAY, session_factory=session_factory
    )

    assert result.current_band is None
    assert result.target_band is None
    assert result.target_gap is None
    assert result.overall_trend == ()
    assert result.skill("listening").latest_band is None
    assert result.skill("listening").trend == ()
    assert result.skill("listening").detail_status == "No enough listening data"
    assert result.skill("speaking").detail_status == "No enough speaking data"
    assert result.reading.attempt_count == 0
    assert result.reading.accuracy is None
    assert result.writing.feedback_count == 0
    assert result.writing.dimension("grammar").latest_band is None
    assert result.behavior.streak_days == 0
    assert result.behavior.recent_minutes == 0
    assert result.behavior.daily_study_minutes is None


def test_tied_frequent_reading_errors_remain_tied(
    session_factory: sessionmaker[Session],
) -> None:
    """Equal highest Reading error counts must not be arbitrarily ranked."""

    user_id = create_user("AnalyticsTies", session_factory)
    with session_factory.begin() as session:
        add_reading_attempt(
            session,
            user_id=user_id,
            score=1,
            total_questions=3,
            results_json=reading_snapshot(
                [
                    ("matching_heading", False),
                    ("matching_heading", False),
                    ("multiple_choice", True),
                ]
            ),
            submitted_at=datetime(2026, 7, 18, 9, 0),
        )
        add_reading_attempt(
            session,
            user_id=user_id,
            score=1,
            total_questions=3,
            results_json=reading_snapshot(
                [
                    ("true_false_not_given", False),
                    ("true_false_not_given", False),
                    ("multiple_choice", True),
                ]
            ),
            submitted_at=datetime(2026, 7, 19, 9, 0),
        )

    result = build_analytics_result(
        user_id, today=TODAY, session_factory=session_factory
    )

    assert result.reading.frequent_error_types == (
        "matching_heading",
        "true_false_not_given",
    )
