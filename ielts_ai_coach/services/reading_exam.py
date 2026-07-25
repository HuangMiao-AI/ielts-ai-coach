"""Application helpers for Reading exam library and session recovery."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.connection import (
    get_session_factory,
    session_scope,
)
from ielts_ai_coach.database.plan_repository import create_plan_task
from ielts_ai_coach.database.reading_library_repository import (
    create_library_plan,
    get_library_plan,
    list_user_tasks_by_subject,
)
from ielts_ai_coach.services.exam_state import (
    ReadingExamSession,
    create_exam_session,
    exam_session_key,
)
from ielts_ai_coach.services.question_bank import (
    ReadingPassage,
    get_reading_passage,
    load_reading_catalog,
)
from ielts_ai_coach.services.reading_practice import (
    ReadingPracticeState,
    get_reading_practice_state,
    resolve_reading_passage,
)
from ielts_ai_coach.services.task_content import serialize_task_content
from ielts_ai_coach.services.task_templates import build_task_content


@dataclass(frozen=True)
class ReadingExamLibraryItem:
    """One original passage plus an optional user-owned practice state."""

    passage: ReadingPassage
    state: ReadingPracticeState | None
    is_submitted: bool

    @property
    def status(self) -> str:
        """Return an honest durable status for the library card."""

        if self.is_submitted:
            return "submitted"
        if self.state is not None:
            return "started"
        return "not_started"


def list_reading_exam_library(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> tuple[ReadingExamLibraryItem, ...]:
    """Return all original passages with only this user's saved state."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        tasks = list_user_tasks_by_subject(
            session,
            user_id=user_id,
            subject="reading",
        )
    states_by_passage: dict[str, ReadingPracticeState] = {}
    for task in tasks:
        passage = resolve_reading_passage(task)
        if passage is None or passage.passage_id in states_by_passage:
            continue
        state = get_reading_practice_state(
            user_id=user_id,
            task_id=task.id,
            session_factory=factory,
        )
        if state is not None:
            states_by_passage[passage.passage_id] = state
    return tuple(
        ReadingExamLibraryItem(
            passage=passage,
            state=states_by_passage.get(passage.passage_id),
            is_submitted=(
                states_by_passage.get(passage.passage_id) is not None
                and states_by_passage[passage.passage_id].score is not None
            ),
        )
        for passage in load_reading_catalog()
    )


def open_reading_library_item(
    *,
    user_id: int,
    passage_id: str,
    session_factory: sessionmaker[Session] | None = None,
) -> ReadingPracticeState:
    """Open or create one user-owned task for a validated catalog passage."""

    passage = get_reading_passage(passage_id)
    factory = session_factory or get_session_factory()
    with factory() as session:
        tasks = list_user_tasks_by_subject(
            session,
            user_id=user_id,
            subject="reading",
        )
    for task in tasks:
        resolved = resolve_reading_passage(task)
        if resolved is not None and resolved.passage_id == passage_id:
            state = get_reading_practice_state(
                user_id=user_id,
                task_id=task.id,
                session_factory=factory,
            )
            if state is not None:
                return state

    catalog = load_reading_catalog()
    passage_index = next(
        index
        for index, item in enumerate(catalog)
        if item.passage_id == passage_id
    )
    active_date = date.today()
    content = build_task_content(
        subject="reading",
        phase="targeted",
        day_offset=passage_index,
        planned_minutes=30,
    )
    with session_scope(factory) as session:
        library_plan = get_library_plan(session, user_id)
        if library_plan is None:
            library_plan = create_library_plan(
                session,
                user_id=user_id,
                active_date=active_date,
            )
        task = create_plan_task(
            session,
            user_id=user_id,
            plan_id=library_plan.id,
            task_date=active_date,
            subject="reading",
            task_type="library_practice",
            title=content.task_title,
            description=serialize_task_content(content),
            planned_minutes=content.planned_minutes,
            priority=passage_index + 1,
        )
        task_id = task.id
    state = get_reading_practice_state(
        user_id=user_id,
        task_id=task_id,
        session_factory=factory,
    )
    if state is None:
        raise RuntimeError("reading_library_task_creation_failed")
    return state


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
