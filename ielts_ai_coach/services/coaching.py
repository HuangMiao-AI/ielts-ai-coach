"""Personalized AI coach orchestration with user-scoped context and quotas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.ai.base import AIProvider, AIProviderError
from ielts_ai_coach.ai.factory import get_ai_provider
from ielts_ai_coach.database.account_repository import get_latest_score, get_profile
from ielts_ai_coach.database.coach_repository import (
    create_coach_message,
    hide_visible_messages,
    list_coach_history,
    list_recent_visible_messages,
)
from ielts_ai_coach.database.connection import get_session_factory, session_scope
from ielts_ai_coach.database.models import CoachMessage
from ielts_ai_coach.database.plan_repository import (
    get_active_plan,
    list_plan_tasks,
    list_study_logs,
)
from ielts_ai_coach.database.usage_repository import (
    get_daily_usage,
    increment_successful_usage,
)
from ielts_ai_coach.services.scoring import SUBJECT_LABELS, analyze_scores


COACH_DAILY_LIMIT = 20
MAX_MESSAGE_LENGTH = 1000
COACH_DISCLAIMER = "以上建议仅供学习参考，不替代正式教师指导或官方评分。"


class CoachServiceError(ValueError):
    """Raised for safe, user-facing coach workflow failures."""


@dataclass(frozen=True)
class CoachReply:
    """One successful coach reply and its remaining daily quota."""

    message: CoachMessage
    remaining: int
    is_mock: bool


def _build_student_context(session: Session, user_id: int, today: date) -> str:
    """Build a concise context using only records owned by one user."""

    profile = get_profile(session, user_id)
    score = get_latest_score(session, user_id)
    plan = get_active_plan(session, user_id)
    lines = ["以下是当前学生已授权用于本次回答的学习数据："]

    if profile:
        lines.append(
            f"- 档案：昵称{profile.nickname}，目标分{profile.target_overall:.1f}，"
            f"考试日期{profile.exam_date.isoformat()}，每日{profile.daily_study_minutes}分钟。"
        )
    else:
        lines.append("- 档案：尚未完善。")

    if score:
        scores = {
            "listening": score.listening,
            "reading": score.reading,
            "writing": score.writing,
            "speaking": score.speaking,
        }
        target = profile.target_overall if profile else score.overall
        diagnosis = analyze_scores(scores, target)
        weak_labels = "、".join(
            SUBJECT_LABELS[subject] for subject in diagnosis.lowest_subjects
        )
        lines.append(
            f"- 最新成绩：听力{score.listening:.1f}，阅读{score.reading:.1f}，"
            f"写作{score.writing:.1f}，口语{score.speaking:.1f}，"
            f"总分{score.overall:.1f}；当前弱项：{weak_labels}。"
        )
    else:
        lines.append("- 成绩：尚未录入。")

    if plan:
        tasks = list_plan_tasks(session, user_id=user_id, plan_id=plan.id)
        task_summary = "；".join(
            f"{task.task_date.isoformat()} {SUBJECT_LABELS.get(task.subject, task.subject)}"
            f"{task.planned_minutes}分钟({task.status})"
            for task in tasks[:12]
        )
        lines.append(f"- 当前七天计划（节选）：{task_summary or '暂无任务'}。")
    else:
        lines.append("- 当前计划：尚未生成。")

    logs = list_study_logs(
        session,
        user_id=user_id,
        start_date=today - timedelta(days=6),
        end_date=today,
    )
    lines.append(
        f"- 最近七天：完成{len(logs)}项任务，实际学习"
        f"{sum(log.minutes for log in logs)}分钟。"
    )
    return "\n".join(lines)


def get_coach_remaining(
    user_id: int,
    *,
    today: date | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> int:
    """Return a user's remaining successful coach messages for today."""

    active_date = today or date.today()
    factory = session_factory or get_session_factory()
    with factory() as session:
        usage = get_daily_usage(
            session, user_id=user_id, usage_date=active_date
        )
        used = usage.coach_success_count if usage else 0
        return max(0, COACH_DAILY_LIMIT - used)


def get_visible_messages(
    user_id: int,
    *,
    limit: int = 100,
    session_factory: sessionmaker[Session] | None = None,
) -> list[CoachMessage]:
    """Return the user's currently visible conversation."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        return list_recent_visible_messages(
            session, user_id=user_id, limit=limit
        )


def get_coach_history(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> list[CoachMessage]:
    """Return all coach messages owned by a user."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        return list_coach_history(session, user_id=user_id)


def clear_current_conversation(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> int:
    """Hide one user's current conversation without deleting its history."""

    factory = session_factory or get_session_factory()
    with session_scope(factory) as session:
        return hide_visible_messages(session, user_id)


def send_coach_message(
    *,
    user_id: int,
    content: str,
    provider: AIProvider | None = None,
    today: date | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> CoachReply:
    """Send one message with owned context and consume quota on success only."""

    cleaned = content.strip()
    if not 1 <= len(cleaned) <= MAX_MESSAGE_LENGTH:
        raise CoachServiceError("invalid_message")
    active_date = today or date.today()
    factory = session_factory or get_session_factory()
    if get_coach_remaining(
        user_id, today=active_date, session_factory=factory
    ) <= 0:
        raise CoachServiceError("quota_exhausted")

    with session_scope(factory) as session:
        context = _build_student_context(session, user_id, active_date)
        recent = list_recent_visible_messages(
            session, user_id=user_id, limit=6
        )
        create_coach_message(
            session, user_id=user_id, role="user", content=cleaned
        )

    messages = [
        {
            "role": "system",
            "content": (
                "你是一名面向中国学生的IELTS学习教练。只依据提供的数据回答，"
                "不编造官方分数，建议应具体、简洁、可执行。"
                f"\n{context}\n回答末尾必须包含：{COACH_DISCLAIMER}"
            ),
        },
        *[
            {"role": message.role, "content": message.content}
            for message in recent
        ],
        {"role": "user", "content": cleaned},
    ]
    active_provider = provider or get_ai_provider()
    try:
        response = active_provider.generate(messages)
    except AIProviderError as error:
        raise CoachServiceError(error.code) from error

    answer = response.content.strip()
    if COACH_DISCLAIMER not in answer:
        answer = f"{answer}\n\n{COACH_DISCLAIMER}"
    with session_scope(factory) as session:
        assistant_message = create_coach_message(
            session,
            user_id=user_id,
            role="assistant",
            content=answer,
            provider=response.provider,
            model_name=response.model_name,
        )
        usage = increment_successful_usage(
            session,
            user_id=user_id,
            usage_date=active_date,
            category="coach",
        )
        remaining = max(0, COACH_DAILY_LIMIT - usage.coach_success_count)
        return CoachReply(
            message=assistant_message,
            remaining=remaining,
            is_mock=active_provider.is_mock,
        )
