"""Read-only user-scoped learning analytics aggregation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.account_repository import list_score_records
from ielts_ai_coach.database.connection import get_session_factory
from ielts_ai_coach.database.exercise_repository import (
    list_task_question_attempts,
)
from ielts_ai_coach.database.plan_repository import list_study_logs
from ielts_ai_coach.database.writing_repository import (
    list_user_writing_feedback,
)
from ielts_ai_coach.services.reading_scoring import deserialize_reading_score
from ielts_ai_coach.services.learner_profiles import get_learner_profile
from ielts_ai_coach.services.scoring import calculate_overall


DETAIL_UNAVAILABLE = "No detailed practice analytics available"
LISTENING_NO_DATA = "No enough listening data"
SPEAKING_NO_DATA = "No enough speaking data"
WRITING_DIMENSIONS = (
    ("task_achievement", "task_response_or_achievement"),
    ("coherence", "coherence_and_cohesion"),
    ("vocabulary", "lexical_resource"),
    ("grammar", "grammatical_range_and_accuracy"),
)


@dataclass(frozen=True)
class ScorePoint:
    """One timestamped IELTS band measurement."""

    recorded_at: datetime
    band: float


@dataclass(frozen=True)
class SkillScoreAnalytics:
    """Latest score and chronological trend for one IELTS skill."""

    skill: str
    latest_band: float | None
    trend: tuple[ScorePoint, ...]
    detail_status: str


@dataclass(frozen=True)
class ReadingAnalytics:
    """Aggregate deterministic Reading-practice evidence."""

    attempt_count: int
    correct: int
    total: int
    accuracy: float | None
    error_counts: tuple[tuple[str, int], ...]
    frequent_error_types: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class WritingDimensionAnalytics:
    """Latest score and chronological trend for one Writing dimension."""

    name: str
    latest_band: float | None
    trend: tuple[ScorePoint, ...]


@dataclass(frozen=True)
class WritingAnalytics:
    """Aggregate structured Writing-feedback evidence."""

    feedback_count: int
    dimensions: tuple[WritingDimensionAnalytics, ...]

    def dimension(self, name: str) -> WritingDimensionAnalytics:
        """Return one named Writing dimension or raise KeyError."""

        for dimension in self.dimensions:
            if dimension.name == name:
                return dimension
        raise KeyError(name)


@dataclass(frozen=True)
class LearningBehavior:
    """Study-time evidence derived from user-owned logs."""

    streak_days: int
    recent_minutes: int
    daily_study_minutes: int | None


@dataclass(frozen=True)
class AnalyticsResult:
    """Complete immutable analytics snapshot for one authenticated user."""

    current_band: float | None
    target_band: float | None
    target_gap: float | None
    overall_trend: tuple[ScorePoint, ...]
    skills: tuple[SkillScoreAnalytics, ...]
    reading: ReadingAnalytics
    writing: WritingAnalytics
    behavior: LearningBehavior

    def skill(self, name: str) -> SkillScoreAnalytics:
        """Return one named skill or raise KeyError."""

        for skill in self.skills:
            if skill.skill == name:
                return skill
        raise KeyError(name)


def _trend(
    records: list[object],
    attribute: str,
    timestamp_attribute: str,
) -> tuple[ScorePoint, ...]:
    """Convert newest-first records into an oldest-first score trend."""

    return tuple(
        ScorePoint(
            recorded_at=getattr(record, timestamp_attribute),
            band=float(getattr(record, attribute)),
        )
        for record in reversed(records)
    )


def _skill_status(skill: str, has_band: bool) -> str:
    """Return the exact availability boundary for Listening and Speaking."""

    if skill == "listening":
        return DETAIL_UNAVAILABLE if has_band else LISTENING_NO_DATA
    if skill == "speaking":
        return DETAIL_UNAVAILABLE if has_band else SPEAKING_NO_DATA
    return ""


def _calculate_streak(study_dates: list[date], *, today: date) -> int:
    """Count distinct consecutive study dates ending today or yesterday."""

    unique_dates = set(study_dates)
    if today in unique_dates:
        cursor = today
    elif today - timedelta(days=1) in unique_dates:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor in unique_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _build_reading_analytics(attempts: list[object]) -> ReadingAnalytics:
    """Aggregate persisted Reading totals and safe snapshot metadata."""

    correct = sum(int(attempt.score) for attempt in attempts)  # type: ignore[attr-defined]
    total = sum(int(attempt.total_questions) for attempt in attempts)  # type: ignore[attr-defined]
    errors: Counter[str] = Counter()
    warnings: set[str] = set()
    for attempt in attempts:
        try:
            snapshot = deserialize_reading_score(attempt.results_json)  # type: ignore[attr-defined]
        except (AttributeError, KeyError, TypeError, ValueError):
            warnings.add("invalid_reading_snapshot")
            continue
        errors.update(
            result.question_type
            for result in snapshot.results
            if not result.is_correct
        )
    error_counts = tuple(sorted(errors.items(), key=lambda item: (-item[1], item[0])))
    highest_error_count = error_counts[0][1] if error_counts else 0
    frequent_error_types = (
        tuple(
            question_type
            for question_type, count in error_counts
            if count == highest_error_count
        )
        if highest_error_count >= 2
        else ()
    )
    return ReadingAnalytics(
        attempt_count=len(attempts),
        correct=correct,
        total=total,
        accuracy=correct / total if total else None,
        error_counts=error_counts,
        frequent_error_types=frequent_error_types,
        warnings=tuple(sorted(warnings)),
    )


def _build_writing_analytics(feedback_records: list[object]) -> WritingAnalytics:
    """Aggregate latest and chronological Writing dimension evidence."""

    latest = feedback_records[0] if feedback_records else None
    dimensions = tuple(
        WritingDimensionAnalytics(
            name=name,
            latest_band=(
                float(getattr(latest, field)) if latest is not None else None
            ),
            trend=_trend(feedback_records, field, "created_at"),
        )
        for name, field in WRITING_DIMENSIONS
    )
    return WritingAnalytics(
        feedback_count=len(feedback_records),
        dimensions=dimensions,
    )


def build_analytics_result(
    user_id: int,
    *,
    today: date | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> AnalyticsResult:
    """Build a read-only, user-isolated analytics snapshot at request time."""

    active_today = today or date.today()
    factory = session_factory or get_session_factory()
    profile = get_learner_profile(user_id, session_factory=factory)
    with factory() as session:
        score_records = list_score_records(session, user_id=user_id)
        attempts = list_task_question_attempts(session, user_id=user_id)
        feedback_records = list_user_writing_feedback(session, user_id=user_id)
        logs = list_study_logs(
            session,
            user_id=user_id,
            start_date=active_today - timedelta(days=89),
            end_date=active_today,
        )

    latest_score = score_records[0] if score_records else None
    target_band = (
        float(profile.target_overall_band) if profile is not None else None
    )
    baseline_scores = (
        {
            skill: profile.current_band(skill)
            for skill in ("listening", "reading", "writing", "speaking")
        }
        if profile is not None
        else {
            skill: None
            for skill in ("listening", "reading", "writing", "speaking")
        }
    )
    complete_baseline = all(
        value is not None for value in baseline_scores.values()
    )
    current_band = (
        float(latest_score.overall)
        if latest_score is not None
        else calculate_overall(
            {
                skill: float(value)
                for skill, value in baseline_scores.items()
                if value is not None
            }
        )
        if complete_baseline
        else None
    )
    skills = tuple(
        SkillScoreAnalytics(
            skill=skill,
            latest_band=(
                float(getattr(latest_score, skill))
                if latest_score is not None
                else baseline_scores[skill]
            ),
            trend=_trend(score_records, skill, "recorded_at"),
            detail_status=_skill_status(
                skill,
                (
                    latest_score is not None
                    or baseline_scores[skill] is not None
                ),
            ),
        )
        for skill in ("listening", "reading", "writing", "speaking")
    )
    return AnalyticsResult(
        current_band=current_band,
        target_band=target_band,
        target_gap=(
            target_band - current_band
            if target_band is not None and current_band is not None
            else None
        ),
        overall_trend=_trend(score_records, "overall", "recorded_at"),
        skills=skills,
        reading=_build_reading_analytics(attempts),
        writing=_build_writing_analytics(feedback_records),
        behavior=LearningBehavior(
            streak_days=_calculate_streak(
                [log.study_date for log in logs], today=active_today
            ),
            recent_minutes=sum(int(log.minutes) for log in logs),
            daily_study_minutes=(
                int(profile.daily_study_minutes) if profile is not None else None
            ),
        ),
    )
