"""Reading library behavior that is independent from seven-day plans."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select
from streamlit.navigation.page import calc_hash

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.models import PlanTask, StudyPlan
from ielts_ai_coach.services.learner_profiles import save_learner_profile
from ielts_ai_coach.services.planning import get_active_plan_data, get_plan_history
from ielts_ai_coach.services.question_bank import load_reading_catalog
from ielts_ai_coach.services.reading_exam import (
    list_reading_exam_library,
    open_reading_library_item,
)
from ielts_ai_coach.services.reading_practice import get_reading_practice_state
from tests.ui_page_helpers import open_authenticated_page


def _user_id(session_factory, username: str) -> int:
    """Create one isolated test user."""

    return register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id


def test_library_lists_all_original_passages_without_a_plan(
    session_factory,
) -> None:
    """A new user can browse every original passage before making a plan."""

    user_id = _user_id(session_factory, "library_new_user")

    items = list_reading_exam_library(
        user_id,
        session_factory=session_factory,
    )

    assert len(items) == len(load_reading_catalog()) == 8
    assert len({item.passage.passage_id for item in items}) == 8
    assert all(item.state is None for item in items)
    assert all(item.status == "not_started" for item in items)
    assert get_active_plan_data(
        user_id,
        session_factory=session_factory,
    ) is None


def test_opening_a_passage_reuses_an_internal_user_owned_task(
    session_factory,
) -> None:
    """Starting the same passage twice must not create duplicate attempts."""

    user_id = _user_id(session_factory, "library_repeat_user")
    passage_id = load_reading_catalog()[-1].passage_id

    first = open_reading_library_item(
        user_id=user_id,
        passage_id=passage_id,
        session_factory=session_factory,
    )
    second = open_reading_library_item(
        user_id=user_id,
        passage_id=passage_id,
        session_factory=session_factory,
    )

    assert first.task.id == second.task.id
    assert first.passage.passage_id == passage_id
    assert get_active_plan_data(
        user_id,
        session_factory=session_factory,
    ) is None
    assert get_plan_history(
        user_id,
        session_factory=session_factory,
    ) == []
    with session_factory() as session:
        assert (
            session.scalar(
                select(func.count(StudyPlan.id)).where(
                    StudyPlan.user_id == user_id,
                    StudyPlan.status == "library",
                )
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count(PlanTask.id)).where(
                    PlanTask.user_id == user_id
                )
            )
            == 1
        )


def test_reading_library_tasks_are_strictly_user_isolated(
    session_factory,
) -> None:
    """One user cannot reuse or load another user's library task."""

    first_user = _user_id(session_factory, "library_user_a")
    second_user = _user_id(session_factory, "library_user_b")
    passage_id = load_reading_catalog()[0].passage_id

    first_state = open_reading_library_item(
        user_id=first_user,
        passage_id=passage_id,
        session_factory=session_factory,
    )
    second_state = open_reading_library_item(
        user_id=second_user,
        passage_id=passage_id,
        session_factory=session_factory,
    )

    assert first_state.task.id != second_state.task.id
    assert (
        get_reading_practice_state(
            user_id=second_user,
            task_id=first_state.task.id,
            session_factory=session_factory,
        )
        is None
    )
    first_items = list_reading_exam_library(
        first_user,
        session_factory=session_factory,
    )
    second_items = list_reading_exam_library(
        second_user,
        session_factory=session_factory,
    )
    assert sum(item.state is not None for item in first_items) == 1
    assert sum(item.state is not None for item in second_items) == 1


def test_reading_page_shows_eight_passages_without_a_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The student-facing route exposes the full library after onboarding."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="profile",
        username="ReadingLibraryPage",
    )
    user_id = app.session_state["user_id"]
    save_learner_profile(
        user_id=user_id,
        display_name="阅读同学",
        current_grade="高二",
        exam_date=None,
        daily_study_minutes=60,
        target_overall_band=7.0,
        current_reading_band=None,
        current_listening_band=None,
        current_writing_band=None,
        current_speaking_band=None,
        onboarding_completed=True,
    )

    app._page_hash = calc_hash("reading")
    app.run(timeout=10)

    assert not app.exception
    assert app.title[0].value == "阅读练习"
    assert len([button for button in app.button if button.label == "开始练习"]) == 8
    for passage in load_reading_catalog():
        assert any(passage.title in item.value for item in app.markdown)
