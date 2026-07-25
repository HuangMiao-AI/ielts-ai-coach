"""Contracts for honest complete, partial, and empty baseline planning."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import func, select
from streamlit.navigation.page import calc_hash
from streamlit.testing.v1 import AppTest

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.models import ScoreRecord
from ielts_ai_coach.services.analytics import build_analytics_result
from ielts_ai_coach.services.home import build_home_snapshot
from ielts_ai_coach.services.learner_profiles import save_learner_profile
from ielts_ai_coach.services.planning import generate_plan
from ielts_ai_coach.services.planning_rules import build_plan_blueprint
from ielts_ai_coach.services.scoring import SUBJECTS
from ielts_ai_coach.services.scores import list_score_history
from tests.ui_page_helpers import open_authenticated_page


def _profile(
    session_factory,
    *,
    username: str,
    reading: float | None = None,
    listening: float | None = None,
    writing: float | None = None,
    speaking: float | None = None,
) -> int:
    """Create a V2 user with independently optional baseline bands."""

    user_id = register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id
    save_learner_profile(
        user_id=user_id,
        display_name=username,
        current_grade="高二",
        exam_date=None,
        daily_study_minutes=60,
        target_overall_band=7.0,
        current_reading_band=reading,
        current_listening_band=listening,
        current_writing_band=writing,
        current_speaking_band=speaking,
        onboarding_completed=True,
        session_factory=session_factory,
    )
    return user_id


def _minutes_by_subject(blueprint) -> dict[str, int]:
    """Aggregate one blueprint's allocated minutes by subject."""

    minutes: dict[str, int] = defaultdict(int)
    for task in blueprint.tasks:
        minutes[task.subject] += task.planned_minutes
    return minutes


def test_empty_baseline_builds_balanced_foundation_exploration_plan() -> None:
    """Missing scores/date never block planning or become numeric evidence."""

    blueprint = build_plan_blueprint(
        scores={subject: None for subject in SUBJECTS},
        target_overall=7.0,
        exam_date=None,
        daily_minutes=60,
        start_date=date(2026, 7, 25),
    )

    assert blueprint.phase == "foundation"
    assert {task.subject for task in blueprint.tasks} == set(SUBJECTS)
    minutes = _minutes_by_subject(blueprint)
    assert max(minutes.values()) - min(minutes.values()) <= 60


def test_partial_baseline_prioritizes_only_a_known_positive_gap() -> None:
    """Unknown skills receive exploration weight rather than a zero band."""

    blueprint = build_plan_blueprint(
        scores={
            "listening": None,
            "reading": 5.0,
            "writing": None,
            "speaking": None,
        },
        target_overall=7.0,
        exam_date=None,
        daily_minutes=90,
        start_date=date(2026, 7, 25),
    )

    minutes = _minutes_by_subject(blueprint)
    assert minutes["reading"] > minutes["listening"]
    assert minutes["reading"] > minutes["writing"]
    assert minutes["reading"] > minutes["speaking"]


def test_generate_plan_with_no_baselines_does_not_create_score_records(
    session_factory,
) -> None:
    """An exploration plan persists tasks but never synthetic scores."""

    user_id = _profile(
        session_factory,
        username="NoBaselinePlan",
    )

    plan = generate_plan(
        user_id,
        today=date(2026, 7, 25),
        session_factory=session_factory,
    )

    assert len(plan.tasks) >= 14
    with session_factory() as session:
        score_count = session.scalar(
            select(func.count(ScoreRecord.id)).where(
                ScoreRecord.user_id == user_id
            )
        )
    assert score_count == 0


def test_partial_baselines_update_latest_skill_values_without_fake_trends(
    session_factory,
) -> None:
    """Runtime Analytics may show baselines but no invented score history."""

    user_id = _profile(
        session_factory,
        username="PartialAnalytics",
        reading=6.5,
        writing=5.5,
    )

    result = build_analytics_result(
        user_id,
        today=date(2026, 7, 25),
        session_factory=session_factory,
    )

    assert result.target_band == 7.0
    assert result.current_band is None
    assert result.skill("reading").latest_band == 6.5
    assert result.skill("writing").latest_band == 5.5
    assert result.skill("listening").latest_band is None
    assert result.skill("listening").detail_status == (
        "No enough listening data"
    )
    assert result.skill("reading").trend == ()
    assert result.overall_trend == ()


def test_complete_baselines_can_produce_current_overall_without_history(
    session_factory,
) -> None:
    """A complete explicit baseline supports current status, not a trend."""

    user_id = _profile(
        session_factory,
        username="CompleteBaseline",
        listening=6.5,
        reading=6.0,
        writing=5.5,
        speaking=6.0,
    )

    result = build_analytics_result(
        user_id,
        today=date(2026, 7, 25),
        session_factory=session_factory,
    )

    assert result.current_band == 6.0
    assert result.target_gap == 1.0
    assert result.overall_trend == ()
    assert result.skill("speaking").detail_status == (
        "No detailed practice analytics available"
    )


def test_home_recommends_plan_without_blocking_on_missing_scores(
    session_factory,
) -> None:
    """A completed profile with no plan recommends planning, not score entry."""

    user_id = _profile(
        session_factory,
        username="HomeNoScore",
    )

    snapshot = build_home_snapshot(
        user_id,
        today=date(2026, 7, 25),
        session_factory=session_factory,
    )

    assert snapshot.recommended_route == "plan"


def test_v2_home_renders_profile_target_and_no_plan_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Home consumes V2 settings while preserving four independent entries."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="home",
        username="V2Home",
    )
    user_id = app.session_state["user_id"]
    save_learner_profile(
        user_id=user_id,
        display_name="首页同学",
        current_grade="高二",
        exam_date=None,
        daily_study_minutes=60,
        target_overall_band=7.5,
        current_reading_band=None,
        current_listening_band=None,
        current_writing_band=None,
        current_speaking_band=None,
        onboarding_completed=True,
    )
    refreshed = AppTest.from_file("app.py")
    refreshed.session_state["authenticated"] = True
    refreshed.session_state["user_id"] = user_id
    refreshed.session_state["username"] = "V2Home"
    refreshed.run(timeout=10)

    assert refreshed.title[0].value == "你好，首页同学"
    assert any(
        metric.label == "目标IELTS分数" and metric.value == "7.5"
        for metric in refreshed.metric
    )
    assert any("没有学习计划" in item.value for item in refreshed.info)


def test_score_record_page_uses_baselines_but_requires_all_real_bands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A partial baseline never silently becomes a complete score record."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="home",
        username="ScoreEntryV2",
    )
    user_id = app.session_state["user_id"]
    save_learner_profile(
        user_id=user_id,
        display_name="完整成绩录入",
        current_grade="高二",
        exam_date=None,
        daily_study_minutes=60,
        target_overall_band=7.0,
        current_reading_band=6.5,
        current_listening_band=None,
        current_writing_band=None,
        current_speaking_band=None,
        onboarding_completed=True,
    )
    refreshed = AppTest.from_file("app.py")
    refreshed.session_state["authenticated"] = True
    refreshed.session_state["user_id"] = user_id
    refreshed.session_state["username"] = "ScoreEntryV2"
    refreshed.run(timeout=10)
    refreshed._page_hash = calc_hash("scores")
    refreshed.run(timeout=10)

    controls = {item.label: item for item in refreshed.selectbox}
    assert controls["阅读"].value == 6.5
    assert controls["听力"].value == "未填写"
    next(
        button
        for button in refreshed.button
        if button.label == "保存并诊断"
    ).click().run(timeout=10)
    assert any("请完整填写四科成绩" in item.value for item in refreshed.error)
    assert list_score_history(user_id) == []
