"""Application helpers for Reading exam library and session recovery."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.services.exam_state import (
    ReadingExamSession,
    create_exam_session,
    exam_session_key,
)
from ielts_ai_coach.services.planning import get_active_plan_data
from ielts_ai_coach.services.reading_practice import (
    ReadingPracticeState,
    get_reading_practice_state,
)


@dataclass(frozen=True)
class ReadingExamLibraryItem:
    """One user-owned Reading task available in the exam library."""

    state: ReadingPracticeState
    is_submitted: bool


def list_reading_exam_library(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> tuple[ReadingExamLibraryItem, ...]:
    """Return eligible Reading tasks from the user's active plan."""

    plan = get_active_plan_data(user_id, session_factory=session_factory)
    if plan is None:
        return ()
    items = []
    for task in plan.tasks:
        if task.subject != "reading":
            continue
        state = get_reading_practice_state(
            user_id=user_id,
            task_id=task.id,
            session_factory=session_factory,
        )
        if state is not None:
            items.append(
                ReadingExamLibraryItem(
                    state=state,
                    is_submitted=state.score is not None,
                )
            )
    return tuple(items)


def load_exam_session(
    store: MutableMapping[str, object],
    *,
    user_id: int,
    task_id: int,
    question_ids: tuple[str, ...],
    duration_seconds: int = 3600,
) -> ReadingExamSession:
    """Recover only an exact user/task/question session or create a new one."""

    key = exam_session_key(user_id, task_id)
    saved = store.get(key)
    if (
        isinstance(saved, ReadingExamSession)
        and saved.user_id == user_id
        and saved.task_id == task_id
        and saved.question_ids == question_ids
    ):
        return saved
    created = create_exam_session(
        user_id=user_id,
        task_id=task_id,
        question_ids=question_ids,
        duration_seconds=duration_seconds,
    )
    store[key] = created
    return created


def save_exam_session(
    store: MutableMapping[str, object],
    session: ReadingExamSession,
) -> None:
    """Persist one immutable session in the caller's transient store."""

    store[exam_session_key(session.user_id, session.task_id)] = session


def clear_exam_session(
    store: MutableMapping[str, object],
    *,
    user_id: int,
    task_id: int,
) -> None:
    """Remove one transient draft without touching durable attempts."""

    store.pop(exam_session_key(user_id, task_id), None)
