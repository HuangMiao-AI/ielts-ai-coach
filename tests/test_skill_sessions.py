"""Pure session-state tests shared by Listening, Writing, and Speaking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ielts_ai_coach.services.skill_sessions import (
    claim_submission,
    draft_key,
    elapsed_seconds,
    move_item,
    release_submission,
    start_session,
)


START = datetime(2026, 7, 19, 9, 0, tzinfo=timezone.utc)


def test_draft_keys_are_isolated_by_user_skill_and_task() -> None:
    """No draft key may be shared across users, skills, or task variants."""

    base = draft_key(1, "writing", "task-1")

    assert base == "skill_draft_1_writing_task-1"
    assert base != draft_key(2, "writing", "task-1")
    assert base != draft_key(1, "speaking", "task-1")
    assert base != draft_key(1, "writing", "task-2")


def test_shared_timer_and_navigation_are_stable_and_bounded() -> None:
    """Repeated starts preserve time and item movement stays in range."""

    session = start_session(
        user_id=1,
        skill="listening",
        task_key="demo-1",
        item_count=4,
        duration_seconds=1800,
        now=START,
    )
    restarted = start_session(session=session, now=START + timedelta(minutes=2))

    assert restarted.started_at == START
    assert elapsed_seconds(restarted, now=START + timedelta(seconds=75)) == 75
    assert move_item(restarted, 99).current_index == 3
    assert move_item(restarted, -99).current_index == 0


def test_submission_guard_blocks_duplicate_click_until_released() -> None:
    """One in-flight submit action must have exactly one owner."""

    store: dict[str, object] = {}

    assert claim_submission(store, "writing-submit-1") is True
    assert claim_submission(store, "writing-submit-1") is False
    release_submission(store, "writing-submit-1")
    assert claim_submission(store, "writing-submit-1") is True
